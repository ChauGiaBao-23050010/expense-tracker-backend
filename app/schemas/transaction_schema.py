from pydantic import BaseModel, Field
from typing import Optional
import datetime
from app.database.models import TransactionType

class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0) # Số tiền luôn dương
    type: TransactionType
    description: Optional[str] = None
    transaction_date: datetime.date

class TransactionCreate(TransactionBase):
    source_account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category_id: Optional[int] = None

class TransactionResponse(TransactionBase):
    id: int
    source_account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True