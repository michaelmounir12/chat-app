from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.user import UserResponse


class ChatRoomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_private: bool = False


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatRoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_private: Optional[bool] = None


class ChatRoomResponse(ChatRoomBase):
    id: int
    created_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    members: List[UserResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class ChatMessageBase(BaseModel):
    content: str = Field(..., min_length=1)


class ChatMessageCreate(ChatMessageBase):
    room_id: int


class ChatMessageResponse(ChatMessageBase):
    id: int
    room_id: int
    sender_id: int
    sender: UserResponse
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
