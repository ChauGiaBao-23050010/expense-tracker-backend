from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal # <--- QUAN TRỌNG: Phải import Decimal
from app.database.models import TransactionType

class TransactionBase(BaseModel):
    # Sử dụng Decimal cho tiền tệ để tránh lỗi làm tròn của float
    amount: Decimal = Field(..., gt=0) 
    type: TransactionType
    description: Optional[str] = None
    transaction_date: datetime

class TransactionCreate(TransactionBase):
    source_account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None # Sử dụng Decimal
    description: Optional[str] = None
    category_id: Optional[int] = None
    source_account_id: Optional[int] = None
    destination_account_id: Optional[int] = None # Thêm trường này để hỗ trợ update đầy đủ
    transaction_date: Optional[datetime] = None
    type: Optional[TransactionType] = None

class TransactionResponse(TransactionBase):
    id: int
    source_account_id: int
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True