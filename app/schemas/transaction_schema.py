from pydantic import BaseModel, Field
from typing import Optional
import datetime
from decimal import Decimal # ĐÃ THÊM IMPORT DECIMAL
from app.database.models import TransactionType

class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0) # ĐÃ SỬA TỪ float SANG Decimal
    type: TransactionType
    description: Optional[str] = None
    transaction_date: datetime.date

class TransactionCreate(TransactionBase):
    source_account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    # THÊM 2 DÒNG NÀY:
    source_account_id: Optional[int] = None
    transaction_date: Optional[datetime.date] = None
    type: Optional[TransactionType] = None
class TransactionResponse(TransactionBase):
    id: int
    source_account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True