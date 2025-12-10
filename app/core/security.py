from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt

# --- Cấu hình Mã hóa Mật khẩu ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Cấu hình JWT ---
# TODO: Chuyển các giá trị này vào file .env sau
JWT_SECRET_KEY = "your-super-secret-key-that-is-long-and-random"  # ĐÂY LÀ KHÓA BÍ MẬT
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token hết hạn sau 30 phút

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu thô với mật khẩu đã mã hóa"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Mã hóa mật khẩu"""
    # Bcrypt chỉ chấp nhận 72 ký tự đầu tiên
    # Chúng ta sẽ cắt chuỗi trước khi băm
    return pwd_context.hash(password[:72])
def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Tạo JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt