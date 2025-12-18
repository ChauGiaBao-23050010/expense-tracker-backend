from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, extract, case, or_
import datetime
import pandas as pd
import io
from typing import Optional
from datetime import date

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
    # Filter dựa trên Source Account thuộc user (Áp dụng cho mọi giao dịch)
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

    else: # time_range == "month" (Mặc định)
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

@router.get("/detailed")
def get_detailed_report(
    start_date: date,
    end_date: date,
    account_id: Optional[int] = Query(None),
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """API cho trang báo cáo chi tiết"""
    
    # Base Query: Join tường minh qua source_account_id
    base_query = db.query(models.Transaction).join(
        models.Account, 
        models.Transaction.source_account_id == models.Account.id # <-- CHỈ RÕ ĐIỀU KIỆN JOIN
    ).filter(
        models.Account.user_id == current_user.id,
        models.Transaction.transaction_date >= start_date,
        models.Transaction.transaction_date <= end_date
    )
    
    if account_id:
        # Lọc giao dịch mà tài khoản được chọn là tài khoản nguồn HOẶC tài khoản đích
        base_query = base_query.filter(
            or_(
                models.Transaction.source_account_id == account_id,
                models.Transaction.destination_account_id == account_id
            )
        )

    # 1. Dữ liệu biểu đồ đường (Dòng tiền theo ngày)
    daily_stats = base_query.with_entities(
        func.date(models.Transaction.transaction_date).label('date'),
        func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
        func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
    ).group_by(func.date(models.Transaction.transaction_date)).order_by('date').all()
    
    line_chart_data = {
        "labels": [str(d.date) for d in daily_stats],
        "income": [float(d.income or 0) for d in daily_stats],
        "expense": [float(d.expense or 0) for d in daily_stats]
    }
    
    # 2. Phân tích chi tiêu theo danh mục (Join tường minh với Category)
    expense_by_cat = base_query.filter(models.Transaction.type == "EXPENSE")\
        .join(models.Category, models.Transaction.category_id == models.Category.id)\
        .with_entities(
            models.Category.name.label('category'),
            func.count(models.Transaction.id).label('count'),
            func.sum(models.Transaction.amount).label('total')
        ).group_by(models.Category.name).order_by(func.sum(models.Transaction.amount).desc()).all()
        
    # 3. Phân tích thu nhập theo danh mục (Join tường minh với Category)
    income_by_cat = base_query.filter(models.Transaction.type == "INCOME")\
        .join(models.Category, models.Transaction.category_id == models.Category.id)\
        .with_entities(
            models.Category.name.label('category'),
            func.count(models.Transaction.id).label('count'),
            func.sum(models.Transaction.amount).label('total')
        ).group_by(models.Category.name).order_by(func.sum(models.Transaction.amount).desc()).all()
    
    # Lấy tổng thu và tổng chi từ dữ liệu đã tính cho biểu đồ đường
    total_income = sum(float(d.income or 0) for d in daily_stats)
    total_expense = sum(float(d.expense or 0) for d in daily_stats)
    net_balance = total_income - total_expense
        
    return {
        "line_chart": line_chart_data,
        "expense_analysis": [dict(row._mapping) for row in expense_by_cat],
        "income_analysis": [dict(row._mapping) for row in income_by_cat],
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": net_balance
        }
    }

@router.get("/export")
def export_transactions(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Xuất toàn bộ giao dịch ra file Excel"""
    
    # 1. Truy vấn dữ liệu (Sửa Join và chọn trường)
    # Cần join tường minh qua source_account_id và sử dụng alias nếu cần join 2 lần
    
    # Tạo alias cho bảng Account khi join lần thứ hai (destination account)
    # Lưu ý: với SQLAlchemy ORM cần dùng sqlalchemy.orm.aliased, không phải .alias() trên model class.
    AccountDestination = aliased(models.Account)
    
    transactions = db.query(
        models.Transaction.transaction_date,
        models.Transaction.description,
        models.Category.name.label("category_name"),
        models.Account.name.label("source_account_name"), # Tài khoản nguồn
        AccountDestination.name.label("destination_account_name"), # Tài khoản đích (dùng alias)
        models.Transaction.type,
        models.Transaction.amount
    ).outerjoin(models.Category, models.Transaction.category_id == models.Category.id)\
     .join(models.Account, models.Transaction.source_account_id == models.Account.id)\
     .outerjoin(AccountDestination, models.Transaction.destination_account_id == AccountDestination.id)\
     .filter(models.Account.user_id == current_user.id)\
     .order_by(models.Transaction.transaction_date.desc()).all()

    # 2. Chuyển đổi sang DataFrame của Pandas
    data = []
    for t in transactions:
        
        account_info = t.source_account_name
        # Xử lý trường hợp chuyển khoản để hiển thị tài khoản đích
        if t.type.value == "TRANSFER":
            dest_name = t.destination_account_name if t.destination_account_name else "Không rõ"
            account_info = f"{t.source_account_name} -> {dest_name}"

        data.append({
            "Ngày giao dịch": t.transaction_date.strftime("%Y-%m-%d %H:%M"),
            "Mô tả": t.description,
            "Danh mục": t.category_name if t.category_name else ("Chuyển khoản" if t.type.value == "TRANSFER" else "Không có"),
            "Tài khoản": account_info,
            "Loại": "Chi tiêu" if t.type.value == "EXPENSE" else ("Thu nhập" if t.type.value == "INCOME" else "Chuyển tiền"),
            "Số tiền": float(t.amount)
        })
    
    df = pd.DataFrame(data)

    # 3. Tạo file Excel trong bộ nhớ (RAM)
    output = io.BytesIO()
    # Sử dụng engine='openpyxl' để xử lý .xlsx
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
