import os
from dotenv import load_dotenv

# Tải các biến từ file .env (chỉ hoạt động ở môi trường local)
load_dotenv()

class Settings:
    # Đọc trực tiếp từ biến môi trường của hệ thống (Render sẽ cung cấp các biến này)
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # Lấy danh sách các origin đã được phân tách
    def get_cors_origins_list(self):
        raw = (self.CORS_ORIGINS or "").strip()

        # Nếu biến môi trường bị set rỗng (""), coi như không cấu hình -> fallback '*'
        if raw == "":
            return ["*"]

        origins: list[str] = []
        for origin in raw.split(","):
            o = origin.strip()
            if not o:
                continue
            # Chuẩn hoá: bỏ dấu '/' cuối để tránh mismatch với header Origin
            # Ví dụ: https://example.vercel.app/ -> https://example.vercel.app
            if o != "*":
                o = o.rstrip("/")
            origins.append(o)

        return origins or ["*"]

settings = Settings()
