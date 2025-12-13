from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
import datetime

from app.database import connection, models
from app.schemas import budget_schema
from app.core import deps

router = APIRouter()

@router.post("/", response_model=budget_schema.BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_in: budget_schema.BudgetCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Tạo ngân sách mới. Chặn nếu đã tồn tại ngân sách cho danh mục này trong tháng này."""
    
    # 1. Kiểm tra danh mục có thuộc về user không
    category = db.query(models.Category).filter(models.Category.id == budget_in.category_id).first()
    if not category or category.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Danh mục không hợp lệ")

    # 2. Kiểm tra trùng lặp (1 user chỉ có 1 ngân sách cho 1 danh mục trong 1 tháng)
    existing_budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.category_id == budget_in.category_id,
        models.Budget.month == budget_in.month,
        models.Budget.year == budget_in.year
    ).first()

    if existing_budget:
        raise HTTPException(status_code=400, detail="Ngân sách cho danh mục này trong tháng này đã tồn tại")

    # 3. Tạo mới
    new_budget = models.Budget(**budget_in.dict(), user_id=current_user.id)
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    
    # Gán thông tin phụ để trả về
    new_budget.spent_amount = 0
    new_budget.category_name = category.name
    new_budget.category_icon = category.icon
    
    return new_budget

@router.get("/", response_model=List[budget_schema.BudgetResponse])
def read_budgets(
    month: int = None,
    year: int = None,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy danh sách ngân sách. Mặc định lấy tháng hiện tại nếu không truyền tham số."""
    if not month or not year:
        now = datetime.datetime.now()
        month = now.month
        year = now.year

    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.month == month,
        models.Budget.year == year
    ).all()

    # Tính toán số tiền đã chi (spent_amount) cho từng ngân sách
    results = []
    for budget in budgets:
        spent = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.source_account.has(user_id=current_user.id),
            models.Transaction.category_id == budget.category_id,
            models.Transaction.type == "EXPENSE", # Chỉ tính chi tiêu
            extract('month', models.Transaction.transaction_date) == month,
            extract('year', models.Transaction.transaction_date) == year
        ).scalar() or 0
        
        # Gán dữ liệu vào object budget để trả về theo schema
        budget.spent_amount = float(spent)
        budget.category_name = budget.category.name
        budget.category_icon = budget.category.icon
        results.append(budget)

    return results

@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ngân sách không tồn tại")
    
    db.delete(budget)
    db.commit()
    return {"message": "Đã xóa thành công"}