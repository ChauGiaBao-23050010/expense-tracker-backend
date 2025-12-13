from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case, text
import datetime
from app.database import connection, models
from app.core import deps

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_stats(
    time_range: str = Query("month", enum=["week", "month", "year"]), # Tham số lọc thời gian
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    now = datetime.datetime.now()
    
    # 1. Xử lý bộ lọc thời gian cho transactions
    filter_conditions = [models.Transaction.source_account.has(user_id=current_user.id)]
    
    if time_range == "week":
        # Lấy từ đầu tuần đến nay
        start_of_week = now - datetime.timedelta(days=now.weekday())
        filter_conditions.append(models.Transaction.transaction_date >= start_of_week.date())
    elif time_range == "month":
        filter_conditions.append(extract('month', models.Transaction.transaction_date) == now.month)
        filter_conditions.append(extract('year', models.Transaction.transaction_date) == now.year)
    elif time_range == "year":
        filter_conditions.append(extract('year', models.Transaction.transaction_date) == now.year)

    # 2. Số liệu tổng quan (Cards)
    # Tổng số dư
    total_balance = db.query(func.sum(models.Account.current_balance))\
        .filter(models.Account.user_id == current_user.id).scalar() or 0
    
    # Tính Tổng Thu/Chi theo time_range (sẽ dùng cho Cards và Biểu đồ Tròn 1)
    # --- ĐOẠN CODE CẬP NHẬT (Thay thế mục 4.3 cũ) ---
    total_stats_for_range = db.query(
        func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
        func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
    ).filter(*filter_conditions).first()

    total_income = total_stats_for_range.income or 0
    total_expense = total_stats_for_range.expense or 0
    # -------------------------------------------------

    # Dựa trên logic frontend của bạn, ta trả về total_income/expense này với tên cũ.
    monthly_income = total_income 
    monthly_expense = total_expense 
    
    # 3. Dữ liệu Biểu đồ Đường (Dòng tiền theo thời gian đã chọn)
    # Group by Date
    daily_stats = db.query(
        func.date(models.Transaction.transaction_date).label('date'),
        func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
        func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
    ).filter(*filter_conditions)\
    .group_by(func.date(models.Transaction.transaction_date))\
    .order_by('date').all()

    line_chart_data = {
        "labels": [str(stat.date) for stat in daily_stats],
        "income": [float(stat.income) for stat in daily_stats],
        "expense": [float(stat.expense) for stat in daily_stats]
    }

    # 4. Dữ liệu 3 Biểu đồ tròn (Theo thời gian đã chọn)
    
    # 4.1 Chi tiêu theo danh mục
    expense_cats = db.query(models.Category.name, func.sum(models.Transaction.amount))\
        .join(models.Transaction)\
        .filter(*filter_conditions, models.Transaction.type == "EXPENSE")\
        .group_by(models.Category.name).all()
    
    # 4.2 Thu nhập theo danh mục
    income_cats = db.query(models.Category.name, func.sum(models.Transaction.amount))\
        .join(models.Transaction)\
        .filter(*filter_conditions, models.Transaction.type == "INCOME")\
        .group_by(models.Category.name).all()

    # 4.3 Tổng Thu vs Chi (Đã tính ở bước 2)

    # 5. Dữ liệu Biểu đồ Cột (Ngân sách - Chỉ tính tháng hiện tại)
    # Lấy ngân sách tháng này
    budget_month_filter = [
        models.Budget.user_id == current_user.id,
        models.Budget.month == now.month,
        models.Budget.year == now.year
    ]
    budgets = db.query(models.Budget).filter(*budget_month_filter).all()
    
    budget_data = {
        "labels": [],
        "spent": [],
        "limit": []
    }
    
    budget_left = 0 # Thêm tính toán budget_left cho Card
    
    # Lọc giao dịch chỉ trong tháng hiện tại cho việc tính Spent
    transaction_month_filter = [
        models.Transaction.source_account.has(user_id=current_user.id),
        models.Transaction.type == "EXPENSE",
        extract('month', models.Transaction.transaction_date) == now.month,
        extract('year', models.Transaction.transaction_date) == now.year
    ]

    for budget in budgets:
        # Tính thực chi cho danh mục này trong tháng
        spent = db.query(func.sum(models.Transaction.amount)).filter(
            *transaction_month_filter,
            models.Transaction.category_id == budget.category_id
        ).scalar() or 0
        
        budget_data["labels"].append(budget.category.name)
        budget_data["spent"].append(float(spent))
        budget_data["limit"].append(float(budget.amount))
        
        budget_left += (budget.amount - spent)

    return {
        "total_balance": total_balance,
        "monthly_income": monthly_income,  # Dữ liệu cho Card 
        "monthly_expense": monthly_expense, # Dữ liệu cho Card
        "budget_left": budget_left,         # Dữ liệu cho Card
        "line_chart": line_chart_data,
        "pie_expense": {"labels": [x[0] for x in expense_cats], "data": [float(x[1]) for x in expense_cats]},
        "pie_income": {"labels": [x[0] for x in income_cats], "data": [float(x[1]) for x in income_cats]},
        "pie_total": {"labels": ["Thu nhập", "Chi tiêu"], "data": [float(total_income), float(total_expense)]},
        "budget_chart": budget_data
    }