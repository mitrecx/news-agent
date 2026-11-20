"""API request/response models"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message"""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request"""

    message: str = Field(..., description="User message", min_length=1)
    history: list[Message] | None = Field(
        default=None, description="Conversation history"
    )
    conversation_id: int | None = Field(
        default=None, description="Conversation ID for history persistence"
    )


class ChatResponse(BaseModel):
    """Chat response"""

    response: str = Field(..., description="Agent response")
    conversation_id: int | None = Field(default=None, description="Conversation ID")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "ok"
    agent_ready: bool


class HotSearchSummaryItem(BaseModel):
    title_hash: str
    title: str
    url: str | None
    description: str
    description_source: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class SingleSummaryResponse(BaseModel):
    status: Literal["generated", "cached"]
    item: HotSearchSummaryItem


class WeiboLoginRequest(BaseModel):
    """Weibo login request"""

    username: str = Field(..., description="Weibo username or phone number")
    password: str = Field(..., description="Weibo password")


class WeiboLoginResponse(BaseModel):
    """Weibo login response"""

    success: bool = Field(..., description="Login success status")
    cookie: str | None = Field(None, description="Extracted Weibo cookie")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error details if failed")
