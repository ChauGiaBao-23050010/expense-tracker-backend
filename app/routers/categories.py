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
    """
    API để tạo một danh mục mới cho người dùng hiện tại.
    """
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
    """
    API để lấy danh sách tất cả các danh mục của người dùng hiện tại.
    """
    categories = db.query(models.Category).filter(models.Category.user_id == current_user.id).all()
    return categories