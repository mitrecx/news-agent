"""User models for authentication"""

from pydantic import BaseModel, Field
from typing import Optional, List


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


# ========== Conversation Models ==========

class ConversationBase(BaseModel):
    """Conversation base model"""
    title: str = Field(..., min_length=1, max_length=200)


class ConversationCreate(ConversationBase):
    """Create conversation model"""
    pass


class ConversationUpdate(BaseModel):
    """Update conversation model"""
    title: str = Field(..., min_length=1, max_length=200)


class Conversation(ConversationBase):
    """Conversation response model"""
    id: int
    user_id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageInDB(BaseModel):
    """Message in database"""
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


class ConversationWithMessages(Conversation):
    """Conversation with its messages"""
    messages: List[MessageInDB]
