from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal # Sử dụng Decimal cho tiền tệ

class BudgetBase(BaseModel):
    # Đã đổi float thành Decimal
    amount: Decimal = Field(..., gt=0) 
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    category_id: int

class BudgetCreate(BudgetBase):
    pass

# --- CLASS MỚI ĐƯỢC THÊM VÀ SỬ DỤNG Decimal ---
class BudgetUpdate(BaseModel):
    # Chỉ cho phép cập nhật amount
    amount: Optional[Decimal] = None
    # Nếu muốn cho phép sửa category_id (dù không khuyến khích), có thể thêm:
    # category_id: Optional[int] = None
    # Lưu ý: Các trường month, year nên bị chặn sửa sau khi tạo.

class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    # Trường này sẽ được tính toán từ backend, không lưu trong bảng Budget
    spent_amount: float = 0.0 
    category_name: str = "" # Để hiển thị tên cho đẹp
    category_icon: Optional[str] = None

    class Config:
        # Cấu hình cho phép Pydantic đọc dữ liệu từ thuộc tính của ORM (SQLAlchemy)
        from_attributes = True
        # Cấu hình JSON encoding để xử lý Decimal
        json_encoders = {
            Decimal: lambda v: float(v),
        }