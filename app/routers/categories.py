from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import connection, models
from app.schemas import category_schema
from app.core import deps

# Tạo một router mới cho categories
router = APIRouter()

@router.post("/", response_model=category_schema.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: category_schema.CategoryCreate, 
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Tạo một danh mục mới cho người dùng hiện tại."""
    # Kiểm tra xem người dùng đã có danh mục trùng tên chưa
    db_category = db.query(models.Category).filter(
        models.Category.user_id == current_user.id,
        models.Category.name == category.name
    ).first()
    
    if db_category:
        raise HTTPException(status_code=400, detail="Tên danh mục đã tồn tại")

    # Tạo đối tượng Category mới và gán owner là người dùng hiện tại
    new_category = models.Category(
        **category.dict(), 
        user_id=current_user.id
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.get("/", response_model=List[category_schema.CategoryResponse])
def read_categories(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy danh sách tất cả các danh mục của người dùng hiện tại."""
    return db.query(models.Category).filter(models.Category.user_id == current_user.id).all()


@router.get("/{category_id}", response_model=category_schema.CategoryResponse)
def read_category_by_id(
    category_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Lấy thông tin chi tiết của một danh mục."""
    category = db.query(models.Category).filter(models.Category.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại")
    
    # Kiểm tra quyền sở hữu
    if category.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tài nguyên này")
        
    return category


@router.put("/{category_id}", response_model=category_schema.CategoryResponse)
def update_category(
    category_id: int,
    category_update: category_schema.CategoryCreate, # Sử dụng CategoryCreate hoặc CategoryUpdate
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Cập nhật thông tin một danh mục."""
    category = db.query(models.Category).filter(models.Category.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại")
    
    if category.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tài nguyên này")

    # Kiểm tra trùng tên danh mục sau khi update (nếu tên bị thay đổi)
    if category_update.name and category_update.name != category.name:
        db_category = db.query(models.Category).filter(
            models.Category.user_id == current_user.id,
            models.Category.name == category_update.name
        ).first()
        if db_category:
            raise HTTPException(status_code=400, detail="Tên danh mục mới đã tồn tại")

    # Cập nhật các trường
    update_data = category_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Xóa một danh mục."""
    category = db.query(models.Category).filter(models.Category.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại")
    
    if category.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tài nguyên này")
    
    # TODO: Cần xử lý các giao dịch liên quan trước khi xóa danh mục (ví dụ: gán cho một danh mục mặc định)
    
    db.delete(category)
    db.commit()
    return {"ok": True}