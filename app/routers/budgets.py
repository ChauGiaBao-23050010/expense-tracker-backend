from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
import datetime

from app.database import connection, models
from app.schemas import budget_schema
from app.core import deps

router = APIRouter()

# --- HELPER FUNCTION: Load Budget details (Category info and Spent amount) ---
def load_budget_details(db: Session, budget: models.Budget, current_user: models.User):
    """Tính toán spent_amount và gán category name/icon cho object Budget"""
    
    # 1. Tính Spent Amount (Dữ liệu này chỉ cần khi trả về, không lưu vào DB)
    spent = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.source_account.has(user_id=current_user.id),
        models.Transaction.category_id == budget.category_id,
        models.Transaction.type == "EXPENSE", # Chỉ tính chi tiêu
        extract('month', models.Transaction.transaction_date) == budget.month,
        extract('year', models.Transaction.transaction_date) == budget.year
    ).scalar() or 0
    
    # 2. Gán thông tin Category
    category = db.query(models.Category).filter(models.Category.id == budget.category_id).first()
    
    budget.spent_amount = float(spent)
    if category:
        budget.category_name = category.name
        budget.category_icon = category.icon
        
    return budget
# -----------------------------------------------------------------------------


@router.post("/", response_model=budget_schema.BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_in: budget_schema.BudgetCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Tạo ngân sách mới. Chặn nếu đã tồn tại ngân sách cho danh mục này trong tháng này."""
    
    # 1. Kiểm tra danh mục có thuộc về user không và phải là loại EXPENSE (nên có)
    category = db.query(models.Category).filter(
        models.Category.id == budget_in.category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        # Thay đổi thông báo để rõ ràng hơn
        raise HTTPException(status_code=400, detail="Danh mục không hợp lệ hoặc không thuộc về bạn.")
    
    if category.type.value != "EXPENSE":
        raise HTTPException(status_code=400, detail="Ngân sách chỉ áp dụng cho Danh mục Chi tiêu.")

    # 2. Kiểm tra trùng lặp (1 user chỉ có 1 ngân sách cho 1 danh mục trong 1 tháng/năm)
    existing_budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.category_id == budget_in.category_id,
        models.Budget.month == budget_in.month,
        models.Budget.year == budget_in.year
    ).first()

    if existing_budget:
        raise HTTPException(status_code=400, detail="Ngân sách cho danh mục này trong tháng/năm này đã tồn tại.")

    # 3. Tạo mới
    new_budget = models.Budget(**budget_in.dict(), user_id=current_user.id)
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    
    # Gán thông tin phụ trước khi trả về
    return load_budget_details(db, new_budget, current_user)


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
    results = [load_budget_details(db, budget, current_user) for budget in budgets]

    return results


@router.get("/{id}", response_model=budget_schema.BudgetResponse)
def read_budget(
    id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy chi tiết một ngân sách theo ID"""
    budget = db.query(models.Budget).filter(
        models.Budget.id == id,
        models.Budget.user_id == current_user.id
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngân sách")
    
    # Gán thông tin phụ trước khi trả về
    return load_budget_details(db, budget, current_user)


@router.put("/{id}", response_model=budget_schema.BudgetResponse)
def update_budget(
    id: int,
    budget_in: budget_schema.BudgetUpdate, # Schema để cập nhật
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Cập nhật một ngân sách (chủ yếu là hạn mức amount)"""
    budget = db.query(models.Budget).filter(
        models.Budget.id == id,
        models.Budget.user_id == current_user.id
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngân sách")
        
    update_data = budget_in.dict(exclude_unset=True)
    
    # Logic kiểm tra trùng lặp nếu người dùng cố gắng thay đổi month/year/category_id
    # Lưu ý: Vì frontend hiện tại chỉ cho phép sửa 'amount', đoạn này có thể lược bỏ
    # nhưng được giữ lại để đảm bảo tính an toàn cho API.
    if 'category_id' in update_data and update_data['category_id'] != budget.category_id:
        # Nếu cố gắng thay đổi category_id, phải kiểm tra lại tính hợp lệ
        category = db.query(models.Category).filter(
            models.Category.id == update_data['category_id'],
            models.Category.user_id == current_user.id,
            models.Category.type.value == "EXPENSE" # Ngân sách phải là Chi tiêu
        ).first()
        if not category:
             raise HTTPException(status_code=400, detail="Danh mục mới không hợp lệ.")
        
        # Kiểm tra trùng lặp với ngân sách khác (cùng tháng, cùng category_id mới)
        existing_check = db.query(models.Budget).filter(
            models.Budget.user_id == current_user.id,
            models.Budget.category_id == update_data['category_id'],
            models.Budget.month == budget.month,
            models.Budget.year == budget.year,
            models.Budget.id != id # Loại trừ chính budget đang sửa
        ).first()
        
        if existing_check:
             raise HTTPException(status_code=400, detail="Ngân sách cho danh mục mới này đã tồn tại trong tháng.")


    # Áp dụng các thay đổi
    for key, value in update_data.items():
        setattr(budget, key, value)
    
    db.commit()
    db.refresh(budget)
    
    # Gán thông tin phụ trước khi trả về
    return load_budget_details(db, budget, current_user)


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    budget = db.query(models.Budget).filter(
        models.Budget.id == budget_id,
        models.Budget.user_id == current_user.id
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Ngân sách không tồn tại")
    
    db.delete(budget)
    db.commit()
    return {"message": "Đã xóa thành công"}