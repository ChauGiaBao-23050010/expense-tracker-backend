from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Import settings để lấy URL đúng (từ Render hoặc Local)
from app.core.config import settings

# --- KHÔNG DÙNG DÒNG NÀY NỮA ---
# SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:112005@localhost:5432/expense_tracker_db"

# Sử dụng URL đã được xử lý trong config
engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Lớp Base mà các model SQLAlchemy sẽ kế thừa
Base = declarative_base()

# Dependency để cung cấp session cho các API endpoint
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()