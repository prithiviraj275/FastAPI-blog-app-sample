import asyncio
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Annotated
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError

from database.database import get_db
import models.models as models
from schemas.schemas import (
    UserCreate,
    UserCreateResponse,
    UserUpdateRequest,
    UserPasswordCreate,
    UserPasswordResponse,
)
from passwordhashing import PasswordManager
from OAuthaccess import get_current_user  # ✅ Import your auth dependency

db_dependency = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/create_user", status_code=status.HTTP_201_CREATED, response_model=UserCreateResponse)
async def create_user(user: UserCreate, db: db_dependency):
    """Public — create account"""
    try:
        db_user = models.User(**user.dict())
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate entry — username or email exists")
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


@router.delete("/delete_user/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user),  # ✅ Auth required
):
    stmt = select(models.User).where(models.User.id == user_id).limit(1)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db.delete(user)
        await db.commit()
        return {"message": f"User with ID {user_id} deleted successfully"}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete user with associated data")
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection error")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.put("/update_user/{user_id}", response_model=UserCreateResponse)
async def update_user(
    user_id: int,
    user: UserUpdateRequest,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user),  # ✅ Auth required
):
    stmt = select(models.User).where(models.User.id == user_id).limit(1)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    try:
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/all_users", response_model=List[UserCreateResponse])
async def get_all_users(
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user),  # ✅ Auth required
):
    try:
        stmt = select(models.User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        return users
    except OperationalError:
        raise HTTPException(status_code=500, detail="Database connection error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}", response_model=UserCreateResponse)
async def get_user(
    user_id: int,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user),  # ✅ Auth required
):
    stmt = select(models.User).where(models.User.id == user_id).limit(1)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Password Endpoints
@router.post("/password/create", response_model=UserPasswordResponse)
async def create_user_password(
    user_password: UserPasswordCreate,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user),  # ✅ Auth required
):
    try:
        up_kwargs = user_password.model_dump()
        new_user_password = models.UserPassword(**up_kwargs)

        raw_pw = getattr(user_password, "password", None) or getattr(user_password, "password_hash", None)
        if raw_pw is None:
            raise HTTPException(status_code=422, detail="Password is required")

        hashed = await asyncio.to_thread(PasswordManager.hash_password, raw_pw)
        new_user_password.password_hash = hashed

        db.add(new_user_password)
        await db.commit()
        await db.refresh(new_user_password)
        return new_user_password
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate entry — user password exists")
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


@router.get("/password/check/{user_id}")
async def check_user_password(
    user_id: int,
    user_pass: str,
    db: db_dependency,
    current_user: UserCreateResponse = Depends(get_current_user),  # ✅ Auth required
):
    stmt = select(models.UserPassword).where(
        models.UserPassword.user_id == user_id,
        models.UserPassword.active == True
    ).limit(1)
    result = await db.execute(stmt)
    user_password = result.scalars().first()

    if not user_password:
        return {"is_valid": False}

    is_valid = await asyncio.to_thread(PasswordManager.verify_password, user_pass, user_password.password_hash)
    return {"is_valid": bool(is_valid)}
