from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import connection, models
from app.schemas import account_schema
from app.core import deps

router = APIRouter()

@router.post("/", response_model=account_schema.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    account: account_schema.AccountCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Tạo một tài khoản (ví tiền) mới cho người dùng hiện tại."""
    # LƯU Ý: Đã sửa từ owner_id thành user_id để khớp với cấu trúc DB (FK là user_id)
    new_account = models.Account(**account.dict(), user_id=current_user.id)
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@router.get("/", response_model=List[account_schema.AccountResponse])
def read_accounts(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy danh sách tất cả các tài khoản của người dùng hiện tại."""
    return db.query(models.Account).filter(models.Account.user_id == current_user.id).all()

@router.get("/{account_id}", response_model=account_schema.AccountResponse)
def read_account_by_id(
    account_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy thông tin chi tiết của một tài khoản."""
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại")
    
    # Kiểm tra quyền sở hữu
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tài nguyên này")
        
    return account

@router.put("/{account_id}", response_model=account_schema.AccountResponse)
def update_account(
    account_id: int,
    account_update: account_schema.AccountUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Cập nhật thông tin một tài khoản."""
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại")
    
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tài nguyên này")

    # Cập nhật các trường đã được thiết lập (exclude_unset=True)
    update_data = account_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    
    # Lưu thay đổi
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Xóa một tài khoản."""
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại")
    
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tài nguyên này")
    
    # TODO: Cần xử lý các giao dịch liên quan trước khi xóa tài khoản (Đây là một lời nhắc quan trọng)
    
    db.delete(account)
    db.commit()
    # Trả về HTTP 204 (No Content)
    return