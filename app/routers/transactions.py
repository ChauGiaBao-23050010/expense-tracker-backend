from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import connection, models
from app.schemas import transaction_schema
from app.core import deps

router = APIRouter()

# --- 1. TẠO GIAO DỊCH MỚI ---
@router.post("/", response_model=transaction_schema.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_in: transaction_schema.TransactionCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Tạo một giao dịch mới (chi tiêu, thu nhập, hoặc chuyển khoản) và cập nhật số dư tài khoản.
    """
    # --- Kiểm tra quyền sở hữu tài khoản nguồn ---
    source_account = db.query(models.Account).filter(models.Account.id == transaction_in.source_account_id).first()
    if not source_account or source_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập vào tài khoản nguồn.")

    # Kiểm tra Category
    if transaction_in.category_id:
        category = db.query(models.Category).filter(models.Category.id == transaction_in.category_id).first()
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập vào danh mục.")

    # --- Xử lý logic nghiệp vụ và cập nhật số dư ---
    
    # 1. Cập nhật số dư tài khoản nguồn
    if transaction_in.type == models.TransactionType.EXPENSE:
        source_account.current_balance -= transaction_in.amount
    elif transaction_in.type == models.TransactionType.INCOME:
        source_account.current_balance += transaction_in.amount
    elif transaction_in.type == models.TransactionType.TRANSFER:
        # 2. Xử lý chuyển khoản
        if not transaction_in.destination_account_id:
            raise HTTPException(status_code=400, detail="Giao dịch chuyển khoản cần có tài khoản đích.")
        
        destination_account = db.query(models.Account).filter(models.Account.id == transaction_in.destination_account_id).first()
        if not destination_account or destination_account.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập vào tài khoản đích.")

        # Trừ tiền ở nguồn, cộng tiền ở đích
        source_account.current_balance -= transaction_in.amount
        destination_account.current_balance += transaction_in.amount
        db.add(destination_account) 

    db.add(source_account) 

    # 3. Tạo bản ghi giao dịch
    new_transaction = models.Transaction(**transaction_in.dict())
    db.add(new_transaction)
    
    db.commit()
    db.refresh(new_transaction)
    
    return new_transaction


# --- 2. LẤY DANH SÁCH GIAO DỊCH THEO TÀI KHOẢN ---
@router.get("/", response_model=List[transaction_schema.TransactionResponse])
def read_transactions_for_account(
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Lấy danh sách các giao dịch của một tài khoản cụ thể.
    """
    # 1. Kiểm tra quyền sở hữu tài khoản
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập vào tài khoản này.")

    # 2. Truy vấn giao dịch: lọc theo source_account_id HOẶC destination_account_id
    transactions = db.query(models.Transaction).filter(
        (models.Transaction.source_account_id == account_id) |
        (models.Transaction.destination_account_id == account_id)
    ).order_by(models.Transaction.transaction_date.desc()).offset(skip).limit(limit).all()
    
    return transactions


# --- 3. CẬP NHẬT GIAO DỊCH ---
@router.put("/{transaction_id}", response_model=transaction_schema.TransactionResponse)
def update_transaction(
    transaction_id: int,
    transaction_in: transaction_schema.TransactionUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Cập nhật thông tin mô tả, ngày tháng hoặc danh mục của giao dịch.
    Lưu ý: Chưa xử lý logic hoàn trả số dư khi đổi số tiền (logic nâng cao).
    """
    # 1. Tìm giao dịch
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    
    # 2. Kiểm tra tồn tại và quyền sở hữu
    if not transaction:
        raise HTTPException(status_code=404, detail="Giao dịch không tồn tại")
    
    # Kiểm tra xem giao dịch này có thuộc về tài khoản của user không
    account = db.query(models.Account).filter(models.Account.id == transaction.source_account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền sửa giao dịch này")

    # 3. Cập nhật dữ liệu (loại bỏ các trường không được gửi lên)
    update_data = transaction_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(transaction, key, value)

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


# --- 4. XÓA GIAO DỊCH ---
@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Xóa hoàn toàn một bản ghi giao dịch.
    """
    # 1. Tìm giao dịch
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Giao dịch không tồn tại")
    
    # 2. Kiểm tra quyền sở hữu thông qua tài khoản nguồn
    account = db.query(models.Account).filter(models.Account.id == transaction.source_account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xóa giao dịch này")

    # 3. Thực hiện xóa
    db.delete(transaction)
    db.commit()
    
    return {"message": "Đã xóa thành công"}