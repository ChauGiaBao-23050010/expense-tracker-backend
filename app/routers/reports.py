from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
import datetime
from app.database import connection, models
from app.core import deps

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_stats(
    # Cập nhật enum chỉ còn day, week, month
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
    
    # Khởi tạo common_filter_line_chart riêng cho các query theo time_range
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

        # Map dữ liệu để đảm bảo đủ 24 giờ
        data_map = {int(stat.hour): stat for stat in hourly_stats}
        for h in range(24):
            line_chart_data["labels"].append(f"{h}h")
            stat = data_map.get(h)
            line_chart_data["income"].append(float(stat.income) if stat and stat.income else 0)
            line_chart_data["expense"].append(float(stat.expense) if stat and stat.expense else 0)

    elif time_range == "week":
        # --- TUẦN NÀY (Nhóm theo Ngày) ---
        start_of_week = today_start - datetime.timedelta(days=today_start.weekday()) # Thứ 2
        common_filter_line_chart.append(models.Transaction.transaction_date >= start_of_week)

        daily_stats = db.query(
            func.date(models.Transaction.transaction_date).label('date'),
            func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
            func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
        ).filter(*common_filter_line_chart)\
        .group_by(func.date(models.Transaction.transaction_date))\
        .order_by('date').all()

        # Tạo map ngày
        data_map = {str(stat.date): stat for stat in daily_stats}
        # Loop từ thứ 2 đến CN
        for i in range(7):
            day = start_of_week + datetime.timedelta(days=i)
            day_str = str(day.date())
            # Format label: "T2 (14/12)"
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
    # 3. Tổng quan số dư (Luôn tính toàn bộ, không theo time_range)
    total_balance = db.query(func.sum(models.Account.current_balance))\
        .filter(models.Account.user_id == current_user.id).scalar() or 0

    # 4. Tổng Thu/Chi trong khoảng thời gian đã chọn (Để hiển thị lên Cards và Biểu đồ tròn)
    # Sử dụng common_filter_line_chart đã được xác định theo time_range
    total_stats = db.query(
        func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
        func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
    ).filter(*common_filter_line_chart).first()

    total_income = total_stats.income or 0
    total_expense = total_stats.expense or 0

    # 5. Dữ liệu Biểu đồ tròn (Theo danh mục)
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
        "budget_left": budget_left, # ĐÃ CẬP NHẬT
        "line_chart": line_chart_data,
        "pie_expense": {"labels": [x[0] for x in expense_cats], "data": [float(x[1]) for x in expense_cats]},
        "pie_income": {"labels": [x[0] for x in income_cats], "data": [float(x[1]) for x in income_cats]},
        "pie_total": {"labels": ["Thu nhập", "Chi tiêu"], "data": [total_income, total_expense]},
        "budget_chart": budget_data # ĐÃ CẬP NHẬT
    }