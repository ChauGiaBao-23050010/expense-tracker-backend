from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import connection, models
from app.schemas import user_schema
from app.core import security

router = APIRouter()

@router.post("/register", response_model=user_schema.UserResponse)
def register_user(user: user_schema.UserCreate, db: Session = Depends(connection.get_db)):
    """
    API để đăng ký người dùng mới.
    """
    # Kiểm tra xem username hoặc email đã tồn tại chưa
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username đã tồn tại")
    
    if user.email:
        db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email đã tồn tại")

    # Mã hóa mật khẩu
    hashed_password = security.get_password_hash(user.password)
    
    # Tạo user mới và lưu vào DB
    new_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user