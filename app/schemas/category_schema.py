from pydantic import BaseModel, Field
from typing import Optional
from app.database.models import TransactionType # Import Enum từ models

# --- Schema Cơ bản ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = None
    # Thêm trường type với giá trị mặc định là CHI TIÊU
    type: TransactionType = TransactionType.EXPENSE 

# --- Schema cho việc Tạo Category (Dữ liệu nhận vào) ---
class CategoryCreate(CategoryBase):
    pass 

# --- Schema cho việc Trả về Dữ liệu (Dữ liệu trả ra) ---
class CategoryResponse(CategoryBase):
    id: int
    user_id: int
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True