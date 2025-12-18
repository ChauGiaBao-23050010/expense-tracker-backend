from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime
import enum # <-- Đảm bảo import enum ở đầu file

# --- Base Class ---
Base = declarative_base()


# --- Enum Types for consistency ---
class TransactionType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"

# THÊM ENUM MỚI
class FrequencyType(str, enum.Enum):
    DAILY = "DAILY"      # Hàng ngày
    WEEKLY = "WEEKLY"    # Hàng tuần
    MONTHLY = "MONTHLY"  # Hàng tháng
    YEARLY = "YEARLY"    # Hàng năm


# --- Table Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # CẬP NHẬT: Thêm back_populates cho giao dịch định kỳ VÀ khoản đầu tư
    accounts = relationship("Account", back_populates="owner")
    categories = relationship("Category", back_populates="owner")
    budgets = relationship("Budget", back_populates="owner")
    recurring_transactions = relationship("RecurringTransaction", back_populates="owner") 
    investments = relationship("Investment", back_populates="owner") # <--- ĐÃ THÊM MỚI
    # 


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)
    current_balance = Column(DECIMAL(precision=15, scale=2), nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="accounts")
    source_transactions = relationship("Transaction", foreign_keys="[Transaction.source_account_id]", back_populates="source_account")
    destination_transactions = relationship("Transaction", foreign_keys="[Transaction.destination_account_id]", back_populates="destination_account")
    
    # CẬP NHẬT: Thêm back_populates cho giao dịch định kỳ
    recurring_source_transactions = relationship("RecurringTransaction", foreign_keys="[RecurringTransaction.source_account_id]", back_populates="source_account")
    recurring_destination_transactions = relationship("RecurringTransaction", foreign_keys="[RecurringTransaction.destination_account_id]", back_populates="destination_account")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String, nullable=False)
    icon = Column(String)
    is_default = Column(Boolean, default=False)
    type = Column(SQLEnum(TransactionType), default=TransactionType.EXPENSE, nullable=False) 

    # Relationships
    owner = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    
    # CẬP NHẬT: Thêm back_populates cho giao dịch định kỳ
    recurring_transactions = relationship("RecurringTransaction", back_populates="category")


class Transaction(Base):
    # Giữ nguyên
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    source_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    amount = Column(DECIMAL(precision=15, scale=2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False)
    description = Column(String)
    transaction_date = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    source_account = relationship("Account", foreign_keys=[source_account_id], back_populates="source_transactions")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], back_populates="destination_transactions")
    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    # Giữ nguyên
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    amount = Column(DECIMAL(precision=15, scale=2), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")


# MÔ HÌNH GIAO DỊCH ĐỊNH KỲ
class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Thông tin để tạo giao dịch
    source_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    # THÊM CỘT TÀI KHOẢN ĐÍCH cho giao dịch TRANSFER định kỳ
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True) 
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    amount = Column(DECIMAL(precision=15, scale=2), nullable=False)
    type = Column(SQLEnum(TransactionType), nullable=False) # Thu/Chi/Chuyển
    description = Column(String)
    
    # Thông tin định kỳ
    frequency = Column(SQLEnum(FrequencyType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    next_run_date = Column(DateTime, nullable=False) # Ngày sẽ chạy tiếp theo
    is_active = Column(Boolean, default=True)
    
    # Relationships ĐÃ SỬA LỖI VÀ TỐI ƯU HÓA back_populates
    owner = relationship("User", back_populates="recurring_transactions")
    category = relationship("Category", back_populates="recurring_transactions")

    # Sử dụng foreign_keys để SQLAlchemy phân biệt giữa source và destination
    source_account = relationship("Account", foreign_keys=[source_account_id], back_populates="recurring_source_transactions")
    destination_account = relationship("Account", foreign_keys=[destination_account_id], back_populates="recurring_destination_transactions")


# --- MÔ HÌNH ĐẦU TƯ MỚI ---

class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False) # VD: Cổ phiếu FPT, Vàng SJC
    type = Column(String) # VD: Cổ phiếu, Vàng, Bất động sản
    initial_value = Column(DECIMAL(precision=15, scale=2), nullable=False) # Vốn ban đầu
    current_value = Column(DECIMAL(precision=15, scale=2), nullable=False) # Giá trị hiện tại
    start_date = Column(DateTime, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="investments") # <-- CẬP NHẬT back_populates
    updates = relationship(
        "InvestmentUpdate", 
        back_populates="investment", 
        cascade="all, delete-orphan" # Xóa các update khi Investment bị xóa
    )


class InvestmentUpdate(Base):
    __tablename__ = "investment_updates"

    id = Column(Integer, primary_key=True, index=True)
    investment_id = Column(Integer, ForeignKey("investments.id"), nullable=False)
    update_date = Column(DateTime, default=datetime.datetime.utcnow)
    value = Column(DECIMAL(precision=15, scale=2), nullable=False) # Giá trị tại thời điểm cập nhật
    notes = Column(String) # Ghi chú (VD: Chốt lời một phần)
    
    # Relationships
    investment = relationship("Investment", back_populates="updates")