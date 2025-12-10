from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Dòng import mới

from app.routers import auth

app = FastAPI(
    title="Expense Tracker API",
    description="API để quản lý chi tiêu cá nhân",
    version="1.0.0"
)

# --- THÊM PHẦN CẤU HÌNH CORS ---
# Danh sách các nguồn (origins) được phép truy cập.
# Dấu "*" có nghĩa là cho phép tất cả, chỉ nên dùng khi phát triển.
origins = [
    "http://localhost",
    "http://localhost:8000",
    # Bạn có thể thêm địa chỉ của frontend sau này, ví dụ: "http://localhost:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Cho phép tất cả các phương thức (GET, POST, etc.)
    allow_headers=["*"], # Cho phép tất cả các header
)
# --- HẾT PHẦN CẤU HÌNH CORS ---


# Kết nối router vào app chính
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

@app.get("/")
def read_root():
    return {"message": "Chào mừng đến với Expense Tracker API"}