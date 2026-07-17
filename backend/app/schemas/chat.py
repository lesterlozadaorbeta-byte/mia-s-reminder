"""Chat/Conversation schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[UUID] = None  # None creates a new conversation


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    intent_detected: Optional[str]
    actions_taken: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str
    summary: Optional[str]
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIAction(BaseModel):
    """An action the AI decided to perform based on user input."""
    action_type: str  # create_reminder, create_event, create_todo, create_alarm, schedule
    parameters: Dict[str, Any]
    confirmation_needed: bool = False
    message: str  # Human-readable description of action


class ChatResponse(BaseModel):
    """Complete response from AI chat."""
    message: MessageResponse
    actions: List[AIAction] = []
    follow_up_questions: List[str] = []
