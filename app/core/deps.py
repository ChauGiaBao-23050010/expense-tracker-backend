from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core import security
from app.database import models, connection

# Trỏ đến API login của bạn
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(connection.get_db)) -> models.User:
    """
    Dependency để lấy user hiện tại từ token.
    Đây là "người gác cổng" cho các API được bảo vệ.
    """
    print("\n--- [DEBUG] BẮT ĐẦU KIỂM TRA TOKEN ---")
    # Chỉ in 30 ký tự đầu của token cho gọn
    print(f"--- [DEBUG] Token nhận được: {token[:30]}...") 

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Xác minh token và lấy user_id trực tiếp
    # Hàm security.verify_token() đã được tối ưu để trả về user_id (string) hoặc None
    user_id = security.verify_token(token)
    
    if user_id is None:
        print("--- [DEBUG] KẾT QUẢ: Token không hợp lệ hoặc hết hạn (verify_token trả về None) ---")
        raise credentials_exception
    
    print(f"--- [DEBUG] Token hợp lệ! User ID từ token: {user_id} ---")
        
    # 2. Truy vấn Database để lấy đối tượng User
    # Chuyển user_id về int vì ID trong DB là int (giả định)
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    
    # 3. Kiểm tra User có tồn tại không
    if user is None:
        print(f"--- [DEBUG] KẾT QUẢ: Không tìm thấy user với ID {user_id} trong DB ---")
        raise credentials_exception
        
    print(f"--- [DEBUG] KẾT QUẢ: Xác thực thành công! User: {user.username} ---\n")
    return user