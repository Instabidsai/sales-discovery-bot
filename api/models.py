"""Pydantic models for API requests/responses."""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat endpoint request model."""
    conversation_id: Optional[str] = Field(
        None,
        description="Existing conversation ID or None to start new"
    )
    message: str = Field(..., description="User message")
    source: Literal["widget", "email", "api"] = Field(
        default="api",
        description="Source of the conversation"
    )


class ChatResponse(BaseModel):
    """Chat endpoint response model."""
    conversation_id: str
    response: str
    stage: Optional[str] = None
    calendly_shown: bool = False


class Message(BaseModel):
    """Message model."""
    id: str
    role: Literal["human", "ai"]
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    """Conversation detail response."""
    conversation_id: str
    messages: List[Message]
    state: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ConversationSummary(BaseModel):
    """Conversation summary for listing."""
    conversation_id: str
    source: str
    message_count: int
    stage: Optional[str]
    has_proposal: bool
    calendly_shown: bool
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Conversation list response."""
    conversations: List[ConversationSummary]
    total: int
    limit: int
    offset: int