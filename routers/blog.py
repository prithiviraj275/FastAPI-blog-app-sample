from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Annotated
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from sqlalchemy.orm import Session
from pydantic import ValidationError
from OAuthaccess import get_current_user
from database.database import get_db
import models.models as models
from schemas.schemas import BlogCreate, BlogResponse, UserCreateResponse

db_dependency = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/blog", tags=["Blogs"])

@router.post("/create", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
def create_blog(blog_data: BlogCreate, db: db_dependency):
    try:
        new_blog = models.Blog(**blog_data.model_dump())
        db.add(new_blog)
        db.commit()
        db.refresh(new_blog)
        return new_blog
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate blog title")
    except DataError:
        db.rollback()
        raise HTTPException(status_code=422, detail="Invalid data type")
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection error")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/all_blogs", response_model=List[BlogResponse])
def get_all_blogs(db: db_dependency, current_user: UserCreateResponse = Depends(get_current_user)):
    try:
        return db.query(models.Blog).all()
    except OperationalError:
        raise HTTPException(status_code=500, detail="Database connection error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{blog_id}", response_model=BlogResponse)
def get_blog(blog_id: int, db: db_dependency):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog

@router.put("/update/{blog_id}", response_model=BlogResponse)
def update_blog(blog_id: int, blog_data: BlogCreate, db: db_dependency):
    db_blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not db_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    for key, value in blog_data.model_dump().items():
        setattr(db_blog, key, value)
    db.commit()
    db.refresh(db_blog)
    return db_blog

@router.delete("/delete/{blog_id}")
def delete_blog(blog_id: int, db: db_dependency):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    try:
        db.delete(blog)
        db.commit()
        return {"message": f"Blog with ID {blog_id} deleted successfully"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete blog with associated data")
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
