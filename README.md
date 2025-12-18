# Expense Tracker Backend API

Đây là phần backend API của ứng dụng quản lý chi tiêu cá nhân "Ví Vàng". Hệ thống được xây dựng trên FastAPI, sử dụng PostgreSQL làm cơ sở dữ liệu, và triển khai các tính năng xác thực, quản lý giao dịch, tài khoản, danh mục, ngân sách, chi tiêu định kỳ, và theo dõi đầu tư.

## 🚀 Công nghệ sử dụng

*   **Framework:** FastAPI (Python)
*   **Database:** PostgreSQL (thông qua SQLAlchemy ORM)
*   **Migrations:** Alembic
*   **Authentication:** JWT (JSON Web Tokens) với mã hóa mật khẩu bcrypt
*   **Validation:** Pydantic
*   **Deployment:** Render.com

## ✨ Tính năng chính

*   **Xác thực người dùng:** Đăng ký, Đăng nhập, Quản lý hồ sơ (JWT).
*   **Quản lý Tài khoản:** Thêm, sửa, xóa các loại ví/tài khoản ngân hàng.
*   **Quản lý Danh mục:** Phân loại chi tiêu/thu nhập, hỗ trợ icon.
*   **Quản lý Giao dịch:** Thêm, sửa, xóa giao dịch (thu nhập, chi tiêu, chuyển tiền nội bộ).
*   **Quản lý Giao dịch Định kỳ:** Tự động tạo giao dịch cho các khoản cố định (tiền nhà, lương...).
*   **Quản lý Ngân sách:** Đặt ngân sách cho từng danh mục, theo dõi tiến độ.
*   **Theo dõi Đầu tư:** Quản lý danh mục tài sản, cập nhật giá trị.
*   **Báo cáo & Thống kê:** Cung cấp dữ liệu chi tiết cho các biểu đồ dòng tiền, cơ cấu thu/chi.
*   **Xuất dữ liệu:** Hỗ trợ xuất dữ liệu giao dịch ra file Excel.

## 🛠 Hướng dẫn Cài đặt và Chạy cục bộ (Local Development)

### Yêu cầu

*   Python 3.9+
*   Poetry (khuyến khích) hoặc pip
*   PostgreSQL Database

### Các bước cài đặt

1.  **Clone repository:**
    ```bash
    git clone https://github.com/YourUsername/expense-tracker-frontend.git
    cd expense-tracker-frontend
    ```
    *(Thay `YourUsername` bằng username GitHub của bạn)*

2.  **Tạo và kích hoạt môi trường ảo:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Cài đặt các thư viện:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Cấu hình biến môi trường:**
    *   Tạo file `.env` ở thư mục gốc của project (ngang hàng với `app/`).
    *   Dán nội dung sau vào và thay thế `YOUR_DB_PASSWORD` bằng mật khẩu PostgreSQL của bạn (VD: `112005`).
    ```env
    DATABASE_URL="postgresql+psycopg2://postgres:YOUR_DB_PASSWORD@localhost:5432/expense_tracker_db" 
    SECRET_KEY="du-an-vi-vang-2025-khoa-luan-ma-nguon-mo-sieu-bao-mat-khong-the-be-khoa"
    ACCESS_TOKEN_EXPIRE_MINUTES=1440
    CORS_ORIGINS="http://localhost:5500,http://localhost:8080" # Hoặc URL của Frontend cục bộ
    ```

5.  **Chuẩn bị Database:**
    *   Đảm bảo dịch vụ PostgreSQL đang chạy.
    *   Mở Terminal và tạo database:
        ```bash
        psql -U postgres
        # Trong psql:
        CREATE DATABASE expense_tracker_db;
        \q
        ```
    *   **Chạy Migrations (tạo bảng):**
        ```bash
        alembic init migrations # (Chỉ chạy lần đầu)
        # Sửa file alembic.ini và migrations/env.py để trỏ đến models.py và DATABASE_URL.
        # (Tham khảo hướng dẫn chi tiết trong các buổi thực hành)
        alembic revision --autogenerate -m "Initial database setup"
        alembic upgrade head
        ```

6.  **Khởi động Server Backend:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    *   Truy cập API Docs tại: `http://localhost:8000/docs`

## 🔗 Liên kết Frontend

*   **Frontend Repository:** [[Link đến GitHub frontend](https://github.com/ChauGiaBao-23050010/expense-tracker-frontend)]
*   **Deployed Frontend:** [[Link Vercel frontend](https://expense-tracker-frontend-h1jsilypt-baos-projects-24c3f38e.vercel.app/)]