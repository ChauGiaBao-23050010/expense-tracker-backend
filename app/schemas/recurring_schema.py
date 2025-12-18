from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date
from decimal import Decimal
from app.database.models import TransactionType, FrequencyType

# --- Base Schema ---

class RecurringBase(BaseModel):
    """Schema cơ sở cho giao dịch định kỳ."""
    
    # Dữ liệu chính
    amount: Decimal = Field(..., gt=0, description="Số tiền giao dịch, phải lớn hơn 0.")
    type: TransactionType = Field(..., description="Loại giao dịch: EXPENSE, INCOME, hoặc TRANSFER.")
    description: Optional[str] = Field(None, max_length=255, description="Mô tả giao dịch.")
    frequency: FrequencyType = Field(..., description="Tần suất lặp lại: DAILY, WEEKLY, MONTHLY, YEARLY.")
    start_date: date = Field(..., description="Ngày bắt đầu chu kỳ giao dịch.")
    is_active: bool = Field(True, description="Trạng thái kích hoạt của giao dịch định kỳ.")

    # Tài khoản & Danh mục
    source_account_id: int = Field(..., description="ID tài khoản nguồn (cũng là tài khoản nhận cho INCOME).")
    destination_account_id: Optional[int] = Field(None, description="ID tài khoản đích (chỉ dùng cho loại TRANSFER).")
    category_id: Optional[int] = Field(None, description="ID danh mục (chỉ dùng cho loại EXPENSE/INCOME).")

    @field_validator('amount', mode='before')
    def validate_amount(cls, value):
        if isinstance(value, str):
            # Xử lý trường hợp số tiền được truyền dưới dạng chuỗi (ví dụ từ form)
            value = value.replace('.', '').replace(',', '')
        try:
            return Decimal(value)
        except:
            raise ValueError('Số tiền phải là một giá trị số hợp lệ.')
            
    @field_validator('category_id', 'destination_account_id')
    def validate_transfer_or_category(cls, value, info):
        # Lấy TransactionType từ dữ liệu
        data = info.data
        tx_type = data.get('type')
        field_name = info.field_name

        if tx_type == TransactionType.TRANSFER:
            # TRANSFER phải có destination_account_id và không có category_id
            if field_name == 'destination_account_id' and value is None:
                raise ValueError("Giao dịch TRANSFER phải có tài khoản đích (destination_account_id).")
            if field_name == 'category_id' and value is not None:
                raise ValueError("Giao dịch TRANSFER không được có danh mục (category_id).")
        else:
            # EXPENSE/INCOME không được có destination_account_id
            if field_name == 'destination_account_id' and value is not None:
                return None # Đặt lại thành None nếu có giá trị
                
        return value

    @field_validator('destination_account_id')
    def validate_distinct_accounts(cls, value, info):
        data = info.data
        if data.get('type') == TransactionType.TRANSFER:
            source_id = data.get('source_account_id')
            destination_id = value
            if source_id == destination_id:
                raise ValueError("Tài khoản nguồn và tài khoản đích không được trùng nhau trong giao dịch TRANSFER.")
        return value


# --- Create/Update Schemas ---

class RecurringCreate(RecurringBase):
    """Schema dùng để tạo mới giao dịch định kỳ."""
    # Kế thừa tất cả các trường bắt buộc từ RecurringBase


class RecurringUpdate(BaseModel):
    """Schema dùng để cập nhật giao dịch định kỳ (tất cả đều là Optional)."""
    
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    description: Optional[str] = Field(None, max_length=255)
    frequency: Optional[FrequencyType] = None
    start_date: Optional[date] = None # <--- ĐÃ THÊM DÒNG NÀY THEO YÊU CẦU
    is_active: Optional[bool] = None
    next_run_date: Optional[date] = None # Chỉ được dùng nội bộ bởi backend, không nên nhận từ client

    source_account_id: Optional[int] = None
    destination_account_id: Optional[int] = None
    category_id: Optional[int] = None

    # Lưu ý: Các validator trong RecurringBase cần được tái áp dụng hoặc xử lý
    # trong logic service/controller khi cập nhật, vì Pydantic không tự động
    # áp dụng validator của Base cho Update khi dùng Optional.


# --- Response Schema ---

class RecurringResponse(RecurringBase):
    """Schema trả về cho người dùng (có thêm các trường chỉ đọc và tên)."""
    
    id: int = Field(..., description="ID của giao dịch định kỳ.")
    next_run_date: date = Field(..., description="Ngày dự kiến giao dịch này được tạo lần tiếp theo.")
    
    # Thêm tên để hiển thị cho đẹp
    category_name: Optional[str] = Field(None, description="Tên danh mục.")
    source_account_name: Optional[str] = Field(None, description="Tên tài khoản nguồn.")
    destination_account_name: Optional[str] = Field(None, description="Tên tài khoản đích (cho TRANSFER).")

    class Config:
        from_attributes = True
        json_encoders = {
            # Giúp Decimal và Date được định dạng đúng khi chuyển sang JSON
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }