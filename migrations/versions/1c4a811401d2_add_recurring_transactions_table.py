"""Add recurring transactions table

Revision ID: 1c4a811401d2
Revises: 671bf8db5524
Create Date: 2025-12-14 00:32:30.889301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# ĐẢM BẢO CÓ DÒNG IMPORT NÀY
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1c4a811401d2'
down_revision: Union[str, Sequence[str], None] = '671bf8db5524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. Định nghĩa Enum ĐÃ TỒN TẠI ('transactiontype')
    # create_type=False: Chỉ tham chiếu, không cố gắng tạo lại
    transaction_type_enum = postgresql.ENUM('INCOME', 'EXPENSE', 'TRANSFER', name='transactiontype', create_type=False)
    
    # 2. Định nghĩa Enum MỚI ('frequencytype')
    # QUAN TRỌNG:
    # - Nếu để create_type=True, lúc op.create_table() chạy, SQLAlchemy sẽ tự tạo TYPE với checkfirst=False
    #   => gây lỗi DuplicateObject nếu TYPE đã tồn tại (như lỗi bạn gặp).
    # - Cách đúng là create_type=False và tự tạo thủ công với checkfirst=True.
    frequency_type_enum = postgresql.ENUM(
        'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY',
        name='frequencytype',
        create_type=False,
    )
    frequency_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table('recurring_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=15, scale=2), nullable=False),
        
        # SỬ DỤNG BIẾN ENUM ĐÃ ĐỊNH NGHĨA
        sa.Column('type', transaction_type_enum, nullable=False),
        
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('source_account_id', sa.Integer(), nullable=False),
        sa.Column('destination_account_id', sa.Integer(), nullable=True),
        
        # SỬ DỤNG BIẾN ENUM MỚI
        sa.Column('frequency', frequency_type_enum, nullable=False),
        
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('next_run_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['destination_account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['source_account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_transactions_id'), 'recurring_transactions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recurring_transactions_id'), table_name='recurring_transactions')
    op.drop_table('recurring_transactions')

    # Xóa enum type (checkfirst=True để không lỗi nếu đã bị drop ở đâu đó)
    frequency_type_enum = postgresql.ENUM(
        'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY',
        name='frequencytype',
        create_type=False,
    )
    frequency_type_enum.drop(op.get_bind(), checkfirst=True)
