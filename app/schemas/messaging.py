from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import UserResponse
from app.db.models import MessageReadStatus, ConversationType


class ConversationBase(BaseModel):
    type: ConversationType = ConversationType.direct
    name: Optional[str] = Field(None, max_length=255)


class ConversationCreate(ConversationBase):
    participant_ids: List[UUID] = Field(..., min_length=1)


class ConversationCreateDirect(BaseModel):
    other_user_id: UUID


class ConversationResponse(ConversationBase):
    id: UUID
    created_at: datetime
    participants: List[UserResponse] = []

    model_config = ConfigDict(from_attributes=True)


class MessageBase(BaseModel):
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    conversation_id: UUID


class MessageResponse(MessageBase):
    id: UUID
    sender_id: UUID
    conversation_id: UUID
    created_at: datetime
    read_status: MessageReadStatus
    sender: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class MessagePayload(BaseModel):
    type: str = "message"
    id: UUID
    sender_id: UUID
    conversation_id: UUID
    content: str
    timestamp: datetime
    read_status: str = "sent"

    model_config = ConfigDict(from_attributes=True)
