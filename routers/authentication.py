from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from schemas.schemas import Login, Token
from database.database import get_db
from models import models
from passwordhashing import PasswordManager
from jwttoken import create_access_token

router = APIRouter(prefix="/authentication", tags=["Authentication"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]

@router.post("/login")
async def login(login_details: Login, db: db_dependency):
    # Find user by email
    result = await db.execute(select(models.User).filter(models.User.email == login_details.email))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find active password for user
    result = await db.execute(
        select(models.UserPassword).filter(
            models.UserPassword.user_id == db_user.id,
            models.UserPassword.active == True
        )
    )
    db_user_password = result.scalars().first()

    if not db_user_password or not PasswordManager.verify_password(login_details.password, db_user_password.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user_id": db_user.id, "username": db_user.username}

@router.post("/generate_token", response_model=Token)
async def get_token( db: db_dependency ,login_details: OAuth2PasswordRequestForm = Depends()    ):
    print(f"Login attempt for user: {login_details.username}")

    # Find user
    result = await db.execute(select(models.User).filter(models.User.email == login_details.username))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find password
    result = await db.execute(
        select(models.UserPassword).filter(
            models.UserPassword.user_id == db_user.id,
            models.UserPassword.active == True
        )
    )
    db_user_password = result.scalars().first()

    if not db_user_password or not PasswordManager.verify_password(login_details.password, db_user_password.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate token
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}
