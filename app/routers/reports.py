from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
import datetime
from app.database import connection, models
from app.core import deps

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # 1. Tổng số dư (Cộng dồn tất cả ví)
    total_balance = db.query(func.sum(models.Account.current_balance))\
        .filter(models.Account.user_id == current_user.id).scalar() or 0

    # 2. Thời gian hiện tại
    now = datetime.datetime.now()
    current_month = now.month
    current_year = now.year

    # 3. Tính Tổng Thu và Tổng Chi trong tháng này
    # Dùng case để tính toán nhanh hơn trong 1 query (hoặc query riêng lẻ)
    monthly_stats = db.query(
        func.sum(case((models.Transaction.type == "INCOME", models.Transaction.amount), else_=0)).label("income"),
        func.sum(case((models.Transaction.type == "EXPENSE", models.Transaction.amount), else_=0)).label("expense")
    ).filter(
        models.Transaction.source_account.has(user_id=current_user.id),
        extract('month', models.Transaction.transaction_date) == current_month,
        extract('year', models.Transaction.transaction_date) == current_year
    ).first()

    return {
        "total_balance": total_balance,
        "monthly_income": monthly_stats.income or 0,
        "monthly_expense": monthly_stats.expense or 0,
        "budget_left": 0 # Tính năng ngân sách làm sau
    }