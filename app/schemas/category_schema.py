from pydantic import BaseModel, Field
from typing import Optional

# --- Schema Cơ bản ---
# Các trường này sẽ được dùng chung
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = None
    # parent_id sẽ được xử lý ở logic, không cần người dùng nhập trực tiếp
    # is_default cũng sẽ do hệ thống quản lý

# --- Schema cho việc Tạo Category (Dữ liệu nhận vào) ---
class CategoryCreate(CategoryBase):
    pass # Hiện tại không cần thêm trường nào khác


# --- Schema cho việc Trả về Dữ liệu (Dữ liệu trả ra) ---
class CategoryResponse(CategoryBase):
    id: int
    user_id: int
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True # Đã sửa từ orm_mode