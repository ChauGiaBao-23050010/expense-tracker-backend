import os
from dotenv import load_dotenv

# Tải các biến từ file .env (chỉ hoạt động ở môi trường local)
load_dotenv()

class Settings:
    # --- XỬ LÝ DATABASE URL ---
    # 1. Lấy từ biến môi trường (Render) hoặc file .env
    # 2. Nếu không có (trường hợp chạy local không env), dùng link localhost mặc định của bạn
    _db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:112005@localhost:5432/expense_tracker_db")
    
    # Render trả về "postgres://", nhưng SQLAlchemy cần "postgresql://"
    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        
    DATABASE_URL: str = _db_url

    # Các biến khác
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_for_dev")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # Lấy danh sách các origin đã được phân tách
    def get_cors_origins_list(self):
        raw = (self.CORS_ORIGINS or "").strip()
        if raw == "":
            return ["*"]
        origins: list[str] = []
        for origin in raw.split(","):
            o = origin.strip()
            if not o:
                continue
            if o != "*":
                o = o.rstrip("/")
            origins.append(o)
        return origins or ["*"]

settings = Settings()