from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Annotated
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from sqlalchemy.orm import Session
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
import models.models as models
from schemas.schemas import UserCreate, UserCreateResponse, UserUpdateRequest, UserPasswordCreate, UserPasswordResponse
from passwordhashing import PasswordManager

db_dependency = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/create_user", status_code=status.HTTP_201_CREATED, response_model=UserCreateResponse)
async def create_user(user: UserCreate, db: db_dependency):
    try:
        db_user = models.User(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate entry — username or email exists")
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

@router.delete("/delete_user/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, db: db_dependency):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db.delete(user)
        db.commit()
        return {"message": f"User with ID {user_id} deleted successfully"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete user with associated data")
    except OperationalError:
        raise HTTPException(status_code=503, detail="Database connection error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.put("/update_user/{user_id}", response_model=UserCreateResponse)
async def update_user(user_id: int, user: UserUpdateRequest, db: db_dependency):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/all_users", response_model=List[UserCreateResponse])
async def get_all_users(db: db_dependency):
    try:
        return db.query(models.User).all()
    except OperationalError:
        raise HTTPException(status_code=500, detail="Database connection error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{user_id}", response_model=UserCreateResponse)
async def get_user(user_id: int, db: db_dependency):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Password Endpoints
@router.post("/password/create", response_model=UserPasswordResponse)
async def create_user_password(user_password: UserPasswordCreate, db: db_dependency):
    try:
        new_user_password = models.UserPassword(**user_password.model_dump())
        new_user_password.password_hash = PasswordManager.hash_password(user_password.password_hash)
        db.add(new_user_password)
        db.commit()
        db.refresh(new_user_password)
        return new_user_password
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate entry — user password exists")
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

@router.get("/password/check/{user_id}")
async def check_user_password(user_id: int, user_pass: str, db: db_dependency):
    user_password = db.query(models.UserPassword).filter(
        models.UserPassword.user_id == user_id,
        models.UserPassword.active == True
    ).first()
    if not user_password:
        return {"is_valid": False}
    return {"is_valid": "Valid Credentials" if PasswordManager.verify_password(user_pass, user_password.password_hash) else "Invalid Credentials"}
