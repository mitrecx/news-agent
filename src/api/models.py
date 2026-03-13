"""API request/response models"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Message(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request"""
    message: str = Field(..., description="User message", min_length=1)
    history: Optional[List[Message]] = Field(default=None, description="Conversation history")
    conversation_id: Optional[int] = Field(default=None, description="Conversation ID for history persistence")


class ChatResponse(BaseModel):
    """Chat response"""
    response: str = Field(..., description="Agent response")
    conversation_id: Optional[int] = Field(default=None, description="Conversation ID")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    agent_ready: bool
