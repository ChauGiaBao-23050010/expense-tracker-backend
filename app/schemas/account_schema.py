from pydantic import BaseModel, Field
from typing import Optional
import datetime
from decimal import Decimal

# --- Schema Cơ bản ---
class AccountBase(BaseModel):
    name: str = Field(..., max_length=100)
    type: Optional[str] = Field(None, max_length=50)

# --- Schema cho việc Tạo Tài khoản ---
class AccountCreate(AccountBase):
    current_balance: Decimal = Field(default=0.0, ge=0)

# --- Schema cho việc Cập nhật Tài khoản (ĐÃ SỬA) ---
class AccountUpdate(BaseModel):
    # Chúng ta không kế thừa AccountBase vì ở Update mọi trường đều là Optional
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    current_balance: Optional[Decimal] = Field(None, ge=0) # Dùng Decimal cho chuẩn xác

# --- Schema cho việc Trả về Dữ liệu ---
class AccountResponse(AccountBase):
    id: int
    user_id: int
    current_balance: Decimal
    created_at: datetime.datetime

    class Config:
        from_attributes = True