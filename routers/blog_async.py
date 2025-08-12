import asyncio
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Annotated
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError

from OAuthaccess import get_current_user
from database.database import get_db
import models.models as models
from schemas.schemas import BlogCreate, BlogResponse, UserCreateResponse

db_dependency = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(prefix="/blog", tags=["Blogs"])


@router.post("/create", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
async def create_blog(
    blog_data: BlogCreate,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user)  # ✅ Auth required
):
    try:
        new_blog = models.Blog(**blog_data.model_dump())
        db.add(new_blog)
        await db.commit()
        await db.refresh(new_blog)
        return new_blog
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate blog title")
    except DataError:
        await db.rollback()
        raise HTTPException(status_code=422, detail="Invalid data type")
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection error")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/all_blogs", response_model=List[BlogResponse])
async def get_all_blogs(
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user)  # ✅ Auth required
):
    try:
        stmt = select(models.Blog)
        result = await db.execute(stmt)
        blogs = result.scalars().all()
        return blogs
    except OperationalError:
        raise HTTPException(status_code=500, detail="Database connection error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{blog_id}", response_model=BlogResponse)
async def get_blog(
    blog_id: int,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user)  # ✅ Auth required
):
    stmt = select(models.Blog).where(models.Blog.id == blog_id).limit(1)
    result = await db.execute(stmt)
    blog = result.scalars().first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog


@router.put("/update/{blog_id}", response_model=BlogResponse)
async def update_blog(
    blog_id: int,
    blog_data: BlogCreate,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user)  # ✅ Auth required
):
    stmt = select(models.Blog).where(models.Blog.id == blog_id).limit(1)
    result = await db.execute(stmt)
    db_blog = result.scalars().first()

    if not db_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    for key, value in blog_data.model_dump().items():
        setattr(db_blog, key, value)

    try:
        await db.commit()
        await db.refresh(db_blog)
        return db_blog
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/delete/{blog_id}")
async def delete_blog(
    blog_id: int,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user)  # ✅ Auth required
):
    stmt = select(models.Blog).where(models.Blog.id == blog_id).limit(1)
    result = await db.execute(stmt)
    blog = result.scalars().first()

    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    try:
        await db.delete(blog)
        await db.commit()
        return {"message": f"Blog with ID {blog_id} deleted successfully"}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete blog with associated data")
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection error")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
