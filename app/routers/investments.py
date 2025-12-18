from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import connection, models
from app.schemas import investment_schema
from app.core import deps

router = APIRouter()

@router.get("/", response_model=List[investment_schema.InvestmentResponse])
def get_all_investments(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy danh sách tất cả các khoản đầu tư"""
    return db.query(models.Investment).filter(models.Investment.user_id == current_user.id).all()

@router.post("/", response_model=investment_schema.InvestmentResponse)
def create_investment(
    investment_in: investment_schema.InvestmentCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Tạo một khoản đầu tư mới"""
    new_investment = models.Investment(
        **investment_in.dict(),
        user_id=current_user.id,
        current_value=investment_in.initial_value # Ban đầu, giá trị hiện tại = vốn
    )
    
    # Tạo bản ghi cập nhật giá trị ban đầu
    initial_update_record = models.InvestmentUpdate(
        investment=new_investment,
        value=investment_in.initial_value
    )
    
    db.add(new_investment)
    db.add(initial_update_record)
    db.commit()
    db.refresh(new_investment)
    return new_investment

@router.get("/{id}", response_model=investment_schema.InvestmentDetailResponse)
def get_investment_detail(
    id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy chi tiết 1 khoản đầu tư và lịch sử cập nhật của nó"""
    # Eager load 'updates' để tránh N+1 query và lấy lịch sử
    investment = db.query(models.Investment).filter(
        models.Investment.id == id, 
        models.Investment.user_id == current_user.id
    ).first()
    
    if not investment:
        raise HTTPException(404, "Không tìm thấy khoản đầu tư")
    return investment

@router.put("/{id}/value", response_model=investment_schema.InvestmentResponse) # Sửa URL thành /value
def update_investment_value(
    id: int,
    update_in: investment_schema.InvestmentUpdateSchema,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Cập nhật giá trị hiện tại của khoản đầu tư và tạo 1 bản ghi lịch sử"""
    investment = db.query(models.Investment).filter(models.Investment.id == id, models.Investment.user_id == current_user.id).first()
    if not investment:
        raise HTTPException(404, "Không tìm thấy khoản đầu tư")
        
    # 1. Cập nhật giá trị hiện tại
    investment.current_value = update_in.current_value
    
    # 2. Tạo bản ghi lịch sử
    new_update_record = models.InvestmentUpdate(
        investment_id=id,
        value=update_in.current_value
    )
    db.add(new_update_record)
    
    db.commit()
    db.refresh(investment)
    return investment

# --- HÀM MỚI: CẬP NHẬT THÔNG TIN CƠ BẢN ---
@router.put("/{id}/info", response_model=investment_schema.InvestmentResponse)
def update_investment_info(
    id: int,
    investment_in: investment_schema.InvestmentCreate, # Tái sử dụng schema tạo mới
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Sửa thông tin cơ bản của khoản đầu tư (tên, loại, vốn, ngày bắt đầu)"""
    investment = db.query(models.Investment).filter(models.Investment.id == id, models.Investment.user_id == current_user.id).first()
    if not investment:
        raise HTTPException(404, "Không tìm thấy khoản đầu tư")
        
    # Lấy dữ liệu update, chỉ lấy những trường được set
    update_data = investment_in.dict(exclude_unset=True) 
    for key, value in update_data.items():
        setattr(investment, key, value)
        
    # Khi sửa initial_value, cần cập nhật current_value và thêm bản ghi update
    if 'initial_value' in update_data:
        investment.current_value = update_data['initial_value']
        # Tùy chọn: Thêm bản ghi lịch sử cho việc reset vốn
        # Tuy nhiên, để đơn giản, ta chỉ cập nhật Investment mà không tạo update record nếu chỉ sửa info
        # Nếu muốn tạo update record, ta sẽ cần thêm logic phức tạp hơn (VD: UpdateValueSchema)

    db.commit()
    db.refresh(investment)
    return investment

# --- HÀM MỚI: XÓA KHOẢN ĐẦU TƯ ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(
    id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Xóa một khoản đầu tư và toàn bộ lịch sử của nó"""
    investment = db.query(models.Investment).filter(models.Investment.id == id, models.Investment.user_id == current_user.id).first()
    if not investment:
        raise HTTPException(404, "Không tìm thấy khoản đầu tư")
        
    # Nhờ cấu hình `cascade="all, delete-orphan"` trong models.py, 
    # các bản ghi InvestmentUpdate liên quan sẽ được xóa tự động.
    db.delete(investment)
    db.commit()
    return None # Trả về 204 No Content