from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime # <--- Thêm import datetime
from decimal import Decimal

# --- Investment Schemas ---
class InvestmentBase(BaseModel):
    name: str
    type: Optional[str] = None
    initial_value: Decimal
    start_date: date

class InvestmentCreate(InvestmentBase):
    pass

class InvestmentUpdateSchema(BaseModel): # Schema để cập nhật giá trị
    current_value: Decimal

class InvestmentResponse(InvestmentBase):
    id: int
    current_value: Decimal
    
    class Config:
        from_attributes = True

# --- Investment Update History Schemas ---
class InvestmentUpdateHistoryBase(BaseModel):
    value: Decimal
    notes: Optional[str] = None

class InvestmentUpdateHistoryCreate(InvestmentUpdateHistoryBase):
    pass

class InvestmentUpdateHistoryResponse(InvestmentUpdateHistoryBase):
    id: int
    update_date: datetime # <--- ĐÃ SỬA THÀNH datetime

    class Config:
        from_attributes = True

# Schema trả về chi tiết một khoản đầu tư kèm lịch sử
class InvestmentDetailResponse(InvestmentResponse):
    updates: List[InvestmentUpdateHistoryResponse] = []