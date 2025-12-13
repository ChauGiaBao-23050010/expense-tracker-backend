from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
import datetime
import pandas as pd
import io

from app.database import connection, models
from app.core import deps

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_stats(
    time_range: str = Query("month", enum=["day", "week", "month"]), 
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Điều kiện lọc cơ bản (User)
    common_filter = [models.Transaction.source_account.has(user_id=current_user.id)]
    
    # 2. Xử lý Logic thời gian cho Biểu đồ Đường (Line Chart)
    line_chart_data = {"labels": [], "income": [], "expense": []}
    
    common_filter_line_chart = list(common_filter)

    if time_range == "day":
        # --- HÔM NAY (Nhóm theo Giờ: 0-23) ---
        common_filter_line_chart.append(models.Transaction.transaction_date >= today_start)
        
        hourly_stats = db.query(
            extract('hour', models.Transaction.transaction_date).label('hour'),
            func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
            func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
        ).filter(*common_filter_line_chart)\
        .group_by('hour').all()

        data_map = {int(stat.hour): stat for stat in hourly_stats}
        for h in range(24):
            line_chart_data["labels"].append(f"{h}h")
            stat = data_map.get(h)
            line_chart_data["income"].append(float(stat.income) if stat and stat.income else 0)
            line_chart_data["expense"].append(float(stat.expense) if stat and stat.expense else 0)

    elif time_range == "week":
        # --- TUẦN NÀY (Nhóm theo Ngày) ---
        start_of_week = today_start - datetime.timedelta(days=today_start.weekday())
        common_filter_line_chart.append(models.Transaction.transaction_date >= start_of_week)

        daily_stats = db.query(
            func.date(models.Transaction.transaction_date).label('date'),
            func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
            func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
        ).filter(*common_filter_line_chart)\
        .group_by(func.date(models.Transaction.transaction_date))\
        .order_by('date').all()

        data_map = {str(stat.date): stat for stat in daily_stats}
        for i in range(7):
            day = start_of_week + datetime.timedelta(days=i)
            day_str = str(day.date())
            weekday_vn = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][day.weekday()]
            label = f"{weekday_vn} ({day.day}/{day.month})"
            
            line_chart_data["labels"].append(label)
            stat = data_map.get(day_str)
            line_chart_data["income"].append(float(stat.income) if stat and stat.income else 0)
            line_chart_data["expense"].append(float(stat.expense) if stat and stat.expense else 0)

    else: # time_range == "month"
        # --- THÁNG NÀY (Nhóm theo Ngày) ---
        common_filter_line_chart.append(extract('month', models.Transaction.transaction_date) == now.month)
        common_filter_line_chart.append(extract('year', models.Transaction.transaction_date) == now.year)

        daily_stats = db.query(
            func.date(models.Transaction.transaction_date).label('date'),
            func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
            func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
        ).filter(*common_filter_line_chart)\
        .group_by(func.date(models.Transaction.transaction_date))\
        .order_by('date').all()
        
        line_chart_data["labels"] = [str(stat.date) for stat in daily_stats]
        line_chart_data["income"] = [float(stat.income) for stat in daily_stats]
        line_chart_data["expense"] = [float(stat.expense) for stat in daily_stats]

    # --- TÍNH TOÁN CÁC SỐ LIỆU TỔNG HỢP ---
    
    # 3. Tổng quan số dư (Toàn bộ)
    total_balance = db.query(func.sum(models.Account.current_balance))\
        .filter(models.Account.user_id == current_user.id).scalar() or 0

    # 4. Tổng Thu/Chi trong khoảng thời gian đã chọn (Sử dụng common_filter_line_chart)
    total_stats = db.query(
        func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
        func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
    ).filter(*common_filter_line_chart).first()

    total_income = total_stats.income or 0
    total_expense = total_stats.expense or 0

    # 5. Dữ liệu Biểu đồ tròn (Theo danh mục - Sử dụng common_filter_line_chart)
    expense_cats = db.query(models.Category.name, func.sum(models.Transaction.amount))\
        .join(models.Transaction)\
        .filter(*common_filter_line_chart, models.Transaction.type == "EXPENSE")\
        .group_by(models.Category.name).all()
    
    income_cats = db.query(models.Category.name, func.sum(models.Transaction.amount))\
        .join(models.Transaction)\
        .filter(*common_filter_line_chart, models.Transaction.type == "INCOME")\
        .group_by(models.Category.name).all()

    # 6. Dữ liệu Biểu đồ Cột (Ngân sách - CHỈ TÍNH THÁNG HIỆN TẠI)
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.month == now.month,
        models.Budget.year == now.year
    ).all()
    
    budget_data = {
        "labels": [],
        "spent": [],
        "limit": []
    }
    
    total_budget_limit = 0
    total_budget_spent = 0
    
    for budget in budgets:
        # Tính thực chi cho danh mục này trong tháng hiện tại
        spent = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.source_account.has(user_id=current_user.id),
            models.Transaction.category_id == budget.category_id,
            models.Transaction.type == "EXPENSE",
            extract('month', models.Transaction.transaction_date) == now.month,
            extract('year', models.Transaction.transaction_date) == now.year
        ).scalar() or 0
        
        budget_data["labels"].append(budget.category.name)
        budget_data["spent"].append(float(spent))
        budget_data["limit"].append(float(budget.amount))
        
        total_budget_limit += budget.amount
        total_budget_spent += spent

    budget_left = total_budget_limit - total_budget_spent

    return {
        "total_balance": total_balance,
        "monthly_income": total_income, 
        "monthly_expense": total_expense,
        "budget_left": budget_left,
        "line_chart": line_chart_data,
        "pie_expense": {"labels": [x[0] for x in expense_cats], "data": [float(x[1]) for x in expense_cats]},
        "pie_income": {"labels": [x[0] for x in income_cats], "data": [float(x[1]) for x in income_cats]},
        "pie_total": {"labels": ["Thu nhập", "Chi tiêu"], "data": [total_income, total_expense]},
        "budget_chart": budget_data
    }

@router.get("/export")
def export_transactions(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Xuất toàn bộ giao dịch ra file Excel"""
    
    # 1. Truy vấn dữ liệu (Join để lấy tên Category và Account thay vì ID)
    transactions = db.query(
        models.Transaction.transaction_date,
        models.Transaction.description,
        models.Category.name.label("category_name"),
        models.Account.name.label("source_account_name"),
        models.Transaction.destination_account_id,
        models.Transaction.type,
        models.Transaction.amount
    ).outerjoin(models.Category, models.Transaction.category_id == models.Category.id)\
     .join(models.Account, models.Transaction.source_account_id == models.Account.id)\
     .filter(models.Account.user_id == current_user.id)\
     .order_by(models.Transaction.transaction_date.desc()).all()

    # Tạo map tài khoản (bao gồm cả tài khoản đích)
    accounts = db.query(models.Account.id, models.Account.name).filter(models.Account.user_id == current_user.id).all()
    account_map = {acc.id: acc.name for acc in accounts}

    # 2. Chuyển đổi sang DataFrame của Pandas
    data = []
    for t in transactions:
        
        account_info = t.source_account_name
        if t.type == models.TransactionType.TRANSFER and t.destination_account_id:
            dest_name = account_map.get(t.destination_account_id, "Không rõ")
            account_info = f"{t.source_account_name} -> {dest_name}"

        data.append({
            "Ngày giao dịch": t.transaction_date.strftime("%Y-%m-%d %H:%M"),
            "Mô tả": t.description,
            "Danh mục": t.category_name if t.category_name else ("Chuyển khoản" if t.type == models.TransactionType.TRANSFER else "Không có"),
            "Tài khoản": account_info,
            "Loại": "Chi tiêu" if t.type == models.TransactionType.EXPENSE else ("Thu nhập" if t.type == models.TransactionType.INCOME else "Chuyển tiền"),
            "Số tiền": float(t.amount)
        })
    
    df = pd.DataFrame(data)

    # 3. Tạo file Excel trong bộ nhớ (RAM)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Giao dịch')
    
    output.seek(0)

    # 4. Trả về response dạng file tải xuống
    headers = {
        'Content-Disposition': f'attachment; filename="bao_cao_chi_tieu_{datetime.date.today()}.xlsx"'
    }
    return StreamingResponse(
        output, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        headers=headers
    )