from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime
from fastapi.security import OAuth2PasswordRequestForm

# --- Schema Cơ bản ---
# Chứa các trường chung nhất của một User
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


# --- Schema cho việc Tạo User (Dữ liệu nhận vào từ API) ---
# Kế thừa từ UserBase và thêm trường password
class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


# --- Schema cho việc Cập nhật User (Dữ liệu nhận vào từ API) ---
# Tất cả các trường đều là Optional, vì người dùng có thể chỉ muốn cập nhật 1 trường
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


# --- Schema cho việc Trả về Dữ liệu User (Dữ liệu trả ra từ API) ---
# Kế thừa từ UserBase, nhưng không bao gồm password
class UserResponse(UserBase):
    id: int
    created_at: datetime.datetime

    # Cấu hình để Pydantic có thể đọc dữ liệu từ object SQLAlchemy
# ... bên trong class UserResponse ...

    class Config:
        # SỬA LẠI DÒNG NÀY
        from_attributes = True