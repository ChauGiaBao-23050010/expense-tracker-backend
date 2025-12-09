from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Chuỗi kết nối đến CSDL PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:112005@localhost:5432/expense_tracker_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

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