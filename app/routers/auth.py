from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import connection, models
from app.schemas import user_schema
from app.core import security

from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import token_schema # Vẫn giữ import này cho hàm register

router = APIRouter()

@router.post("/register", response_model=user_schema.UserResponse)
def register_user(user: user_schema.UserCreate, db: Session = Depends(connection.get_db)):
    """
    API để đăng ký người dùng mới.
    """
    # Kiểm tra xem username đã tồn tại chưa
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username đã tồn tại")
    
    # Kiểm tra Email (nếu có)
    if user.email:
        db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
        # Lưu ý: Theo sơ đồ ERD, email là UK, nên cần kiểm tra
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

@router.post("/login") # ĐÃ BỎ response_model=token_schema.Token
def login_for_access_token(db: Session = Depends(connection.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    API để đăng nhập và nhận JWT token.
    FastAPI sẽ tự động tạo form với username và password.
    """
    # Xác thực người dùng (Tìm user theo username và kiểm tra password)
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # Kiểm tra: 1. User có tồn tại không? 2. Mật khẩu có khớp không?
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai username hoặc password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Tạo access token (sử dụng user.id làm subject/chủ thể)
    # LƯU Ý: Đây là điểm mấu chốt, đảm bảo ID người dùng được đưa vào token
    access_token = security.create_access_token(subject=user.id)
    
    # Trả về Token và loại Token (bearer)
    return {"access_token": access_token, "token_type": "bearer"}