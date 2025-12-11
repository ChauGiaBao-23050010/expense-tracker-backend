from pydantic import BaseModel, Field
from typing import Optional
import datetime
from decimal import Decimal # ĐÃ THÊM IMPORT DECIMAL

class AccountBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: Optional[str] = Field(None, max_length=50)

class AccountCreate(AccountBase):
    current_balance: Decimal = Field(default=0.0, ge=0) # ĐÃ SỬA SANG Decimal VÀ THÊM validate ge=0

class AccountUpdate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    user_id: int
    current_balance: Decimal # ĐÃ SỬA SANG Decimal
    created_at: datetime.datetime

    class Config:
        from_attributes = True