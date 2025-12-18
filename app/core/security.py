from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Union, Any, Optional
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

# Cấu hình mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cấu hình JWT
# TODO: SAU NÀY SẼ CHUYỂN VÀO FILE .ENV
JWT_SECRET_KEY = "bat-tai-ban-cung-bat-giai-nhan-tam" 
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token hết hạn sau 24 giờ

# Định nghĩa lược đồ OAuth2 cho FastAPI để trích xuất token từ header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") 

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu thô với mật khẩu đã mã hóa"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Mã hóa mật khẩu"""
    return pwd_context.hash(password[:72]) # Cắt ngắn để tránh lỗi bcrypt

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT access token. 'subject' chính là user_id"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Payload chỉ cần chứa 'exp' (thời gian hết hạn) và 'sub' (subject - định danh người dùng)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """
    Giải mã và xác minh JWT token.
    Nếu hợp lệ, trả về subject (user_id).
    Nếu không hợp lệ, trả về None.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        # Lấy subject từ payload (chính là user ID)
        subject = payload.get("sub")
        if subject is None:
            return None
        return subject
    except JWTError:
        return None