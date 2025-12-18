from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Đọc cấu hình từ Settings (Để lấy biến môi trường từ Render)
from app.core.config import settings

# Import các module router
from app.routers import (
    auth, 
    users, 
    categories, 
    accounts, 
    transactions, 
    reports, 
    budgets, 
    recurring, 
    investments
)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Ví Vàng - Expense Tracker API",
    description="API để quản lý tài chính cá nhân, được xây dựng bằng FastAPI và PostgreSQL.",
    version="1.0.0"
)

# --- CẤU HÌNH CORS (Kết hợp Local và Environment Variable) ---
# 1. Các domain mặc định cho Localhost (Dev)
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
]

# 2. Thêm domain từ biến môi trường trên Render (Nếu có)
# Giúp bạn không cần sửa code mỗi khi Vercel đổi link
if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS:
    # Nếu settings trả về list, cộng vào luôn
    if isinstance(settings.CORS_ORIGINS, list):
        origins.extend(settings.CORS_ORIGINS)
    # Nếu settings trả về string (ví dụ từ file .env), tách ra và cộng vào
    elif isinstance(settings.CORS_ORIGINS, str):
        origins.extend([origin.strip() for origin in settings.CORS_ORIGINS.split(",")])

# 3. Thêm cứng link Vercel hiện tại để chắc chắn chạy được (Backup)
origins.extend([
    "https://expense-tracker-frontend-virid-nine.vercel.app",
    "https://expense-tracker-frontend-virid-nine.vercel.app/"
])

# Loại bỏ các domain trùng lặp (nếu có)
origins = list(set(origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
# ----------------------------------------------------

# Kết nối (include) tất cả các router
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(recurring.router, prefix="/recurring", tags=["Recurring Transactions"])
app.include_router(budgets.router, prefix="/budgets", tags=["Budgets"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(investments.router, prefix="/investments", tags=["Investments"])

# Endpoint gốc
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Chào mừng đến với API Ví Vàng!", "status": "ok"}

print("--- SERVER KHOI DONG THANH CONG ---")
print(f"CORS origins allowed: {len(origins)} domains")