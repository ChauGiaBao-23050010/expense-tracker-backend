from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import deps
from app.schemas import user_schema
from app.database import models

router = APIRouter()

# SỬA LẠI HÀM NÀY
@router.get("/me", response_model=user_schema.UserResponse)
def read_users_me(current_user: models.User = Depends(deps.get_current_user)):
    """
    API để lấy thông tin của người dùng hiện tại (đã đăng nhập).
    """
    # Không cần làm gì thêm, chỉ cần trả về user đã được dependency xử lý
    return current_user