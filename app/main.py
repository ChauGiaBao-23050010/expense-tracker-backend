from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import mới cho cấu hình OpenAPI tùy chỉnh
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles # Import cần thiết nếu bạn muốn phục vụ file tĩnh

# Import tất cả các router: auth, users, categories, accounts, transactions
from app.routers import auth, users, categories, accounts, transactions 

# KHỞI TẠO APP VỚI CẤU HÌNH TÙY CHỈNH CHO SECURITY SCHEME
app = FastAPI(
    title="Expense Tracker API",
    description="API để quản lý chi tiêu cá nhân",
    version="1.0.0",
    docs_url=None, # Tắt docs mặc định để cấu hình lại
    redoc_url=None # Tắt redoc mặc định
)

# --- THÊM PHẦN CẤU HÌNH CORS ---
# Danh sách các nguồn (origins) được phép truy cập.
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:3000",
    # Bạn có thể thêm địa chỉ của frontend sau này
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Cho phép tất cả các phương thức (GET, POST, etc.)
    allow_headers=["*"], # Cho phép tất cả các header
)
# --- HẾT PHẦN CẤU HÌNH CORS ---


# --- CẤU HÌNH OPENAPI TÙY CHỈNH CHO BEARER AUTHENTICATION ---
def custom_openapi():
    """Tạo OpenAPI schema và thêm BearerAuth Security Scheme."""
    if app.openapi_schema:
        return app.openapi_schema
    
    # 1. Tạo schema mặc định
    openapi_schema = get_openapi(
        title="Expense Tracker API",
        version="1.0.0",
        description="API để quản lý chi tiêu cá nhân",
        routes=app.routes,
    )
    
    # 2. Thêm Security Scheme (Bearer Auth)
    if "components" not in openapi_schema:
         openapi_schema["components"] = {}
         
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Gán lại schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Thêm lại endpoint cho Swagger UI với cấu hình mới ---
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Tạo endpoint /docs để hiển thị Swagger UI, sử dụng CDN mặc định."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        # Đã bỏ qua các tham số swagger_js_url và swagger_css_url để dùng CDN mặc định.
    )

# --- Kết nối router vào app chính ---
# Đã bao gồm tất cả 5 router: Auth, Users, Categories, Accounts, Transactions
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(accounts.router, prefix="/accounts", tags=["Accounts"]) 
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])

@app.get("/")
def read_root():
    return {"message": "Chào mừng đến với Expense Tracker API"}