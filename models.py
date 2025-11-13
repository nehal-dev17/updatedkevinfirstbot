from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProfileUpdate(BaseModel):
    """User profile update model"""
    age: Optional[int] = Field(None, ge=1, le=150, description="User age")
    background: Optional[str] = Field(None, max_length=500, description="User background")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

    class Config:
        json_schema_extra = {
            "example": {
                "age": 30,
                "background": "Software Engineer",
                "preferences": {"meditation": True, "exercise": True}
            }
        }


class ProfileResponse(BaseModel):
    """User profile response model"""
    user_id: int
    age: Optional[int] = None
    background: Optional[str] = "Other"
    preferences: Optional[Dict[str, Any]] = {}
    history: Optional[List[Dict[str, Any]]] = []
    summaries: Optional[List[Dict[str, Any]]] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I'm feeling stressed lately. Can you help?"
            }
        }


class ChatResponse(BaseModel):
    """Chat response model"""
    reply: str
    timestamp: str


class ConversationItem(BaseModel):
    """Single conversation item model"""
    user_id: int
    timestamp: str
    role: str
    content: str
    keywords: Optional[List[str]] = []


class HistoryResponse(BaseModel):
    """Conversation history response model"""
    user_id: int
    items: List[ConversationItem]
    total_count: int


class ConversationSummary(BaseModel):
    """Conversation summary model"""
    summary: str
    key_topics: List[str]
    sentiment: str
    message_count: int
    created_at: str


class DeleteHistoryResponse(BaseModel):
    """Delete history response model"""
    status: str
    message: str
    user_id: int
    deleted_count: int
    summary: ConversationSummary


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: str