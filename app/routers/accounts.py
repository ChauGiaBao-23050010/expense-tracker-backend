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
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    return accounts