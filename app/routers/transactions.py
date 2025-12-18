from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional 
from datetime import date # Nhớ import thêm date

from app.database import connection, models
from app.schemas import transaction_schema
from app.core import deps

router = APIRouter()

# --- 1. TẠO GIAO DỊCH MỚI (Giữ nguyên) ---
@router.post("/", response_model=transaction_schema.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_in: transaction_schema.TransactionCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    source_account = db.query(models.Account).filter(models.Account.id == transaction_in.source_account_id).first()
    if not source_account or source_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập vào tài khoản nguồn.")

    if transaction_in.category_id:
        category = db.query(models.Category).filter(models.Category.id == transaction_in.category_id).first()
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập vào danh mục.")

    if transaction_in.type == models.TransactionType.EXPENSE:
        source_account.current_balance -= transaction_in.amount
    elif transaction_in.type == models.TransactionType.INCOME:
        source_account.current_balance += transaction_in.amount
    elif transaction_in.type == models.TransactionType.TRANSFER:
        if not transaction_in.destination_account_id:
            raise HTTPException(status_code=400, detail="Giao dịch chuyển khoản cần có tài khoản đích.")
        
        destination_account = db.query(models.Account).filter(models.Account.id == transaction_in.destination_account_id).first()
        if not destination_account or destination_account.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập vào tài khoản đích.")

        source_account.current_balance -= transaction_in.amount
        destination_account.current_balance += transaction_in.amount
        db.add(destination_account) 

    db.add(source_account) 
    new_transaction = models.Transaction(**transaction_in.dict())
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction


# --- 2. LẤY DANH SÁCH GIAO DỊCH (ĐÃ CẬP NHẬT để hỗ trợ Optional account_id và bộ lọc nâng cao) ---
@router.get("/", response_model=List[transaction_schema.TransactionResponse])
def read_transactions(
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    type: Optional[models.TransactionType] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Lấy danh sách giao dịch với bộ lọc nâng cao.
    """
    # 1. Base Query: Join với Account để lọc theo User
    query = db.query(models.Transaction).join(
        models.Account, 
        models.Transaction.source_account_id == models.Account.id
    ).filter(models.Account.user_id == current_user.id)

    # 2. Áp dụng các bộ lọc nếu có
    if account_id:
        # Kiểm tra quyền sở hữu (dù đã join, nhưng kiểm tra tường minh tốt hơn)
        account = db.query(models.Account).filter(models.Account.id == account_id).first()
        if not account or account.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập tài khoản này")

        query = query.filter(
            (models.Transaction.source_account_id == account_id) |
            (models.Transaction.destination_account_id == account_id)
        )
    
    if category_id:
        query = query.filter(models.Transaction.category_id == category_id)
        
    if type:
        query = query.filter(models.Transaction.type == type)
        
    if search:
        # Tìm kiếm không phân biệt hoa thường trong description
        query = query.filter(models.Transaction.description.ilike(f"%{search}%"))
        
    if start_date:
        query = query.filter(models.Transaction.transaction_date >= start_date)
        
    if end_date:
        query = query.filter(models.Transaction.transaction_date <= end_date)

    # 3. Sắp xếp và Phân trang
    transactions = query.order_by(models.Transaction.transaction_date.desc())\
                         .offset(skip).limit(limit).all()
    
    return transactions


# --- 3. CẬP NHẬT GIAO DỊCH (LOGIC THÔNG MINH MỚI) ---
@router.put("/{transaction_id}", response_model=transaction_schema.TransactionResponse)
def update_transaction(
    transaction_id: int,
    transaction_in: transaction_schema.TransactionUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # 1. Lấy giao dịch cũ
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Giao dịch không tồn tại")
    
    # 2. Lấy tài khoản cũ để hoàn tác số dư
    old_account = db.query(models.Account).filter(models.Account.id == transaction.source_account_id).first()
    if not old_account or old_account.user_id != current_user.id:
        # Nếu tài khoản cũ thuộc về user khác (không nên xảy ra nếu logic tạo đúng), hoặc không tồn tại
        raise HTTPException(status_code=403, detail="Không quyền truy cập tài khoản cũ")

    # --- BƯỚC 3: HOÀN TÁC GIAO DỊCH CŨ (Revert) ---
    if transaction.type == models.TransactionType.EXPENSE:
        old_account.current_balance += transaction.amount
    elif transaction.type == models.TransactionType.INCOME:
        old_account.current_balance -= transaction.amount
    
    # --- BƯỚC 4: CHUẨN BỊ DỮ LIỆU MỚI ---
    update_data = transaction_in.dict(exclude_unset=True)
    
    # Cập nhật các trường thông tin vào object transaction (lúc này transaction.amount đã mang giá trị mới)
    for key, value in update_data.items():
        setattr(transaction, key, value)

    # --- BƯỚC 5: ÁP DỤNG GIAO DỊCH MỚI (Apply) ---
    # Kiểm tra xem người dùng có đổi tài khoản khác không
    new_account_id = update_data.get("source_account_id", transaction.source_account_id)
    new_account = db.query(models.Account).filter(models.Account.id == new_account_id).first()
    
    if not new_account or new_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Tài khoản mới không hợp lệ")

    # Tính toán lại trên tài khoản mới với số tiền mới và loại giao dịch mới
    if transaction.type == models.TransactionType.EXPENSE:
        new_account.current_balance -= transaction.amount
    elif transaction.type == models.TransactionType.INCOME:
        new_account.current_balance += transaction.amount

    # Lưu tất cả thay đổi vào Database
    db.add(old_account)
    if new_account.id != old_account.id: 
        db.add(new_account)
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
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Giao dịch không tồn tại")
    
    account = db.query(models.Account).filter(models.Account.id == transaction.source_account_id).first()
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xóa giao dịch này")

    # TỐI ƯU: Logic Revert số dư trước khi xóa
    if transaction.type == models.TransactionType.EXPENSE:
        account.current_balance += transaction.amount
    elif transaction.type == models.TransactionType.INCOME:
        account.current_balance -= transaction.amount
    db.add(account)

    db.delete(transaction)
    db.commit()
    
    return {"message": "Đã xóa thành công và cập nhật lại số dư"}