from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import connection, models
from app.schemas import transaction_schema
from app.core import deps

router = APIRouter()

@router.post("/", response_model=transaction_schema.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: transaction_schema.TransactionCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # TODO: Sẽ thêm logic kiểm tra account, category có thuộc về user không
    # TODO: Sẽ thêm logic cập nhật current_balance của account
    
    new_transaction = models.Transaction(**transaction.dict())
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction

@router.get("/", response_model=List[transaction_schema.TransactionResponse])
def read_transactions(
    account_id: int, # Lọc giao dịch theo tài khoản
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # TODO: Sẽ thêm logic kiểm tra account_id có thuộc về user không
    transactions = db.query(models.Transaction).filter(models.Transaction.source_account_id == account_id).all()
    return transactions