from pydantic import BaseModel, Field
from typing import Optional

class BudgetBase(BaseModel):
    amount: float = Field(..., gt=0)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    category_id: int

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount: Optional[float] = None

class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    # Trường này sẽ được tính toán từ backend, không lưu trong bảng Budget
    spent_amount: float = 0.0 
    category_name: str = "" # Để hiển thị tên cho đẹp
    category_icon: Optional[str] = None

    class Config:
        from_attributes = True