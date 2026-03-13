"""User models for authentication"""

from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    """User registration model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str


class User(BaseModel):
    """User response model"""
    id: int
    username: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


class UserInDB(User):
    """User with password hash (internal use only)"""
    hashed_password: str


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    user: User


class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None
    user_id: Optional[int] = None
