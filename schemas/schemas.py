from pydantic import BaseModel
from typing import Optional
from datetime import datetime 
class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False

    class Config:
            orm_mode = True

class UserCreateResponse(BaseModel):
    id: int | None = None
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False

    class Config:
            orm_mode = True


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

    class Config:
        orm_mode = True


class BlogCreate(BaseModel):
    title: str
    content: str
    author_id: int

class BlogResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime

    class Config:
        orm_mode = True  # So Pydantic can read SQLAlchemy objects

class UserPasswordCreate(BaseModel):
    user_id: int
    password_hash: str

    class Config:
        orm_mode = True

class UserPasswordResponse(BaseModel):
    id: int
    user_id: int
    password_hash: str
    created_at: datetime
    active: bool

    class Config:
        orm_mode = True

class Login(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
