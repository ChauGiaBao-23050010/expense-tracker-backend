from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date # Thêm date
from dateutil.relativedelta import relativedelta 
from sqlalchemy import or_

from app.database import connection, models
from app.schemas import recurring_schema
from app.core import deps

router = APIRouter()

# --- HÀM LOGIC TỰ ĐỘNG (ENGINE) ---
def process_due_transactions(db: Session, user_id: int):
    """Kiểm tra và tạo giao dịch cho các khoản định kỳ đã đến hạn"""
    # Lấy thời điểm hiện tại
    now = datetime.now()
    
    # Lấy các khoản định kỳ đang hoạt động
    active_items = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == user_id,
        models.RecurringTransaction.is_active == True
    ).all()

    processed_count = 0

    for item in active_items:
        # Nếu next_run_date <= hôm nay thì chạy
        # So sánh theo ngày (date()) để bỏ qua phần giờ, chỉ quan tâm đến ngày
        while item.next_run_date.date() <= now.date():
            
            print(f"--- [AUTO] Tạo giao dịch định kỳ: {item.description} cho ngày {item.next_run_date.strftime('%Y-%m-%d')} ---")

            # 1. Tạo Giao dịch thật
            # Bỏ dòng user_id=user_id vì nó không cần thiết hoặc có thể được xử lý bởi logic khác 
            # (ví dụ: tự động gán user_id từ source_account/destination_account, 
            # hoặc vì mục đích đơn giản hóa việc tạo Transaction)
            new_trans = models.Transaction(
                # user_id=user_id, # <--- ĐÃ XÓA DÒNG NÀY THEO YÊU CẦU
                source_account_id=item.source_account_id,
                destination_account_id=item.destination_account_id,
                category_id=item.category_id,
                amount=item.amount,
                type=item.type,
                description=f"[Định kỳ] {item.description}" if item.description else "[Giao dịch Định kỳ]",
                transaction_date=item.next_run_date # Giữ nguyên ngày giờ của lịch hẹn
            )
            
            # 2. Cập nhật số dư tài khoản (Bắt đầu Transaction)
            source_acc = db.query(models.Account).filter(models.Account.id == item.source_account_id).first()
            
            # Nếu tài khoản nguồn bị xóa, chỉ vô hiệu hóa giao dịch định kỳ này
            if not source_acc:
                item.is_active = False
                processed_count += 1
                db.add(item)
                print(f"--- [AUTO] Vô hiệu hóa: {item.id}. Tài khoản nguồn bị xóa.")
                # Cần commit sớm để lưu trạng thái is_active=False
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    print(f"Lỗi commit vô hiệu hóa: {e}")
                continue

            # Thay đổi số dư
            if item.type == models.TransactionType.EXPENSE:
                source_acc.current_balance -= item.amount
            
            elif item.type == models.TransactionType.INCOME:
                source_acc.current_balance += item.amount
            
            elif item.type == models.TransactionType.TRANSFER and item.destination_account_id:
                # Logic chuyển tiền
                dest_acc = db.query(models.Account).filter(models.Account.id == item.destination_account_id).first()
                if dest_acc:
                    # Rút tiền từ nguồn, Thêm tiền vào đích
                    source_acc.current_balance -= item.amount
                    dest_acc.current_balance += item.amount
                    db.add(dest_acc)
                else:
                    # Nếu tài khoản đích bị xóa, chỉ vô hiệu hóa giao dịch định kỳ này
                    item.is_active = False
                    db.add(item)
                    db.add(source_acc)
                    processed_count += 1
                    print(f"--- [AUTO] Vô hiệu hóa: {item.id}. Tài khoản đích bị xóa.")
                    try:
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        print(f"Lỗi commit vô hiệu hóa: {e}")
                    continue
            
            db.add(source_acc)
            db.add(new_trans)
            
            # 3. Tính ngày chạy tiếp theo (Cập nhật lịch)
            current_run = item.next_run_date
            
            # Hàm tính ngày chạy tiếp theo dựa trên frequency
            def calculate_next_run(current_dt, frequency_type):
                if frequency_type == models.FrequencyType.DAILY:
                    return current_dt + timedelta(days=1)
                elif frequency_type == models.FrequencyType.WEEKLY:
                    return current_dt + timedelta(weeks=1)
                elif frequency_type == models.FrequencyType.MONTHLY:
                    # Sử dụng relativedelta để xử lý tháng chính xác (ví dụ: 31/01 -> 28/02)
                    return current_dt + relativedelta(months=1)
                elif frequency_type == models.FrequencyType.YEARLY:
                    return current_dt + relativedelta(years=1)
                return current_dt

            # Tính ngày chạy tiếp theo
            item.next_run_date = calculate_next_run(current_run, item.frequency)
            db.add(item) # Thêm item đã cập nhật next_run_date vào session
            processed_count += 1
            
    if processed_count > 0:
        try:
            db.commit()
            print(f"--- [AUTO] Đã tạo thành công {processed_count} giao dịch và cập nhật lịch ---")
        except Exception as e:
            db.rollback()
            print(f"--- [AUTO] LỖI FATAL khi commit giao dịch định kỳ: {e} ---")
            
    return processed_count


# --- LOGIC TÍNH TOÁN NGÀY CHẠY TIẾP THEO (Dùng cho POST/PUT) ---
def get_next_run_from_start(start_date: date, frequency: models.FrequencyType) -> date:
    """Tính ngày chạy tiếp theo (next_run_date) gần nhất kể từ hôm nay."""
    today = datetime.now().date()
    
    # Chuyển start_date thành datetime.date (nếu nó là datetime) hoặc giữ nguyên date
    next_run = start_date
    
    # Vòng lặp để tìm ngày chạy gần nhất trong tương lai hoặc hôm nay
    while next_run < today:
        current_run_dt = datetime(next_run.year, next_run.month, next_run.day)
        
        if frequency == models.FrequencyType.DAILY:
            next_run = (current_run_dt + timedelta(days=1)).date()
        elif frequency == models.FrequencyType.WEEKLY:
            next_run = (current_run_dt + timedelta(weeks=1)).date()
        elif frequency == models.FrequencyType.MONTHLY:
            next_run = (current_run_dt + relativedelta(months=1)).date()
        elif frequency == models.FrequencyType.YEARLY:
            next_run = (current_run_dt + relativedelta(years=1)).date()
        else:
            # Dừng nếu frequency không hợp lệ
            break
            
    # Nếu start_date là hôm nay hoặc trong tương lai, next_run chính là start_date
    if start_date >= today:
        return start_date
        
    return next_run


# --- API ENDPOINTS ---

@router.get("/", response_model=List[recurring_schema.RecurringResponse])
def read_recurring(
    is_active: Optional[bool] = None,
    type: Optional[models.TransactionType] = None,
    search: Optional[str] = None,
    frequency: Optional[models.FrequencyType] = None,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # 1. Chạy logic xử lý giao dịch đến hạn
    process_due_transactions(db, current_user.id)
    
    # 2. Bắt đầu query
    query = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == current_user.id
    )

    # 3. Áp dụng filter
    if is_active is not None:
        query = query.filter(models.RecurringTransaction.is_active == is_active)
    if type:
        query = query.filter(models.RecurringTransaction.type == type)
    if frequency:
        query = query.filter(models.RecurringTransaction.frequency == frequency)
    if search:
        search_pattern = f"%{search}%"
        # Bổ sung tìm kiếm theo description và amount (dưới dạng chuỗi)
        query = query.filter(
            or_(
                models.RecurringTransaction.description.ilike(search_pattern),
                models.RecurringTransaction.amount.cast(models.db_connection.String).ilike(search_pattern)
            )
        )

    # 4. Sắp xếp và lấy kết quả
    items = query.order_by(models.RecurringTransaction.next_run_date.asc()).all()
    
    # 5. Map tên hiển thị (cho response schema)
    for item in items:
        item.category_name = item.category.name if item.category else None
        item.source_account_name = item.source_account.name if item.source_account else "Tài khoản (Nguồn) đã xóa"
        item.destination_account_name = item.destination_account.name if item.destination_account else None
        
    return items


@router.post("/", response_model=recurring_schema.RecurringResponse)
def create_recurring(
    item_in: recurring_schema.RecurringCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # Tính next_run_date ban đầu dựa trên start_date
    next_run_date = get_next_run_from_start(item_in.start_date, item_in.frequency)
    
    # Chuyển đổi next_run_date (date) thành datetime.datetime
    next_run_dt = datetime.combine(next_run_date, datetime.min.time())

    new_item = models.RecurringTransaction(
        **item_in.model_dump(), # Thay .dict() bằng .model_dump() cho Pydantic v2
        user_id=current_user.id,
        next_run_date=next_run_dt
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Map tên hiển thị
    new_item.category_name = new_item.category.name if new_item.category else None
    new_item.source_account_name = new_item.source_account.name if new_item.source_account else None
    new_item.destination_account_name = new_item.destination_account.name if new_item.destination_account else None
    
    return new_item

@router.put("/{id}", response_model=recurring_schema.RecurringResponse)
def update_recurring(
    id: int,
    item_in: recurring_schema.RecurringUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Cập nhật thông tin chi tiêu định kỳ"""
    item = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == id,
        models.RecurringTransaction.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch định kỳ")
    
    # Lấy dữ liệu cần cập nhật
    update_data = item_in.model_dump(exclude_unset=True) # Thay .dict() bằng .model_dump()
    
    # --- LOGIC CẦN THIẾT: TÍNH LẠI next_run_date NẾU frequency HOẶC start_date THAY ĐỔI ---
    if 'frequency' in update_data or 'start_date' in update_data:
        # Lấy giá trị mới hoặc giá trị cũ hiện tại
        new_start_date = update_data.get('start_date', item.start_date)
        new_frequency = update_data.get('frequency', item.frequency)
        
        # Nếu start_date được gửi lên là datetime, cần chuyển về date
        if isinstance(new_start_date, datetime):
            new_start_date = new_start_date.date()
        elif isinstance(new_start_date, date):
            pass # Giữ nguyên là date
        else:
             # Nếu không thay đổi start_date, lấy giá trị cũ (đã là datetime) và chuyển về date
             new_start_date = item.start_date.date() 

        # 1. Tính toán ngày chạy tiếp theo (date object)
        next_run_date_obj = get_next_run_from_start(new_start_date, new_frequency)
        
        # 2. Chuyển đổi thành datetime (để khớp với kiểu dữ liệu trong DB)
        # Giữ nguyên phần giờ-phút-giây của next_run_date cũ nếu không phải là lần đầu chạy
        # Hoặc dùng 00:00:00 nếu item.next_run_date không phải là datetime (tùy thuộc vào model SQLAlchemy)
        
        # Ở đây ta sẽ sử dụng 00:00:00 vì logic tự động (process_due_transactions) đã sử dụng datetime.min.time() 
        # và timedelta/relativedelta giữ nguyên phần giờ nếu có. 
        # Để đơn giản, ta sẽ đặt lại giờ về 00:00:00 của ngày mới.
        update_data['next_run_date'] = datetime.combine(next_run_date_obj, datetime.min.time())

    # Cập nhật dữ liệu vào model
    for key, value in update_data.items():
        if key == 'start_date' and isinstance(value, date):
            # Nếu start_date là date object, cần chuyển thành datetime để khớp với cột trong DB
            # Tuy nhiên, trong schema RecurringCreate start_date là date, trong model DB thường là datetime.
            # Ta sẽ chuyển date từ input thành datetime để lưu trữ.
            setattr(item, key, datetime.combine(value, datetime.min.time()))
        else:
            setattr(item, key, value)


    db.commit()
    db.refresh(item)
    
    # Map tên hiển thị (cho response)
    item.category_name = item.category.name if item.category else None
    item.source_account_name = item.source_account.name if item.source_account else None
    item.destination_account_name = item.destination_account.name if item.destination_account else None
    
    return item

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(
    id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    item = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == id,
        models.RecurringTransaction.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy")
    
    db.delete(item)
    db.commit()
    # FastAPI sẽ tự trả về 204 No Content