from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.chat_repository import ChatRoomRepository, ChatMessageRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ChatRoomCreate, ChatRoomUpdate, ChatRoomResponse, ChatMessageCreate, ChatMessageResponse


class ChatService:
    def __init__(self, db: AsyncSession):
        self.room_repo = ChatRoomRepository(db)
        self.message_repo = ChatMessageRepository(db)
        self.user_repo = UserRepository(db)
    
    async def create_room(self, room_data: ChatRoomCreate, creator_id: UUID) -> ChatRoomResponse:
        existing_room = await self.room_repo.get_by_name(room_data.name)
        if existing_room:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room name already exists"
            )
        
        room_dict = room_data.model_dump()
        room_dict["created_by_id"] = creator_id
        
        room = await self.room_repo.create(room_dict)
        
        await self.room_repo.add_member(room.id, creator_id)
        
        room = await self.room_repo.get_by_id(room.id)
        return ChatRoomResponse.model_validate(room)
    
    async def get_room_by_id(self, room_id: int) -> ChatRoomResponse:
        room = await self.room_repo.get_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        return ChatRoomResponse.model_validate(room)
    
    async def get_user_rooms(self, user_id: UUID) -> List[ChatRoomResponse]:
        rooms = await self.room_repo.get_user_rooms(user_id)
        return [ChatRoomResponse.model_validate(room) for room in rooms]
    
    async def update_room(self, room_id: int, room_data: ChatRoomUpdate, user_id: UUID) -> ChatRoomResponse:
        room = await self.room_repo.get_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        if room.created_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only room creator can update the room"
            )
        
        update_data = room_data.model_dump(exclude_unset=True)
        
        if "name" in update_data:
            existing_room = await self.room_repo.get_by_name(update_data["name"])
            if existing_room and existing_room.id != room_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Room name already exists"
                )
        
        updated_room = await self.room_repo.update(room_id, update_data)
        return ChatRoomResponse.model_validate(updated_room)
    
    async def add_member_to_room(self, room_id: int, user_id: UUID, requester_id: UUID) -> ChatRoomResponse:
        room = await self.room_repo.get_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        if room.is_private and room.created_by_id != requester_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only room creator can add members to private rooms"
            )
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        success = await self.room_repo.add_member(room_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add member to room"
            )
        
        updated_room = await self.room_repo.get_by_id(room_id)
        return ChatRoomResponse.model_validate(updated_room)
    
    async def remove_member_from_room(self, room_id: int, user_id: UUID, requester_id: UUID) -> ChatRoomResponse:
        room = await self.room_repo.get_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        if room.created_by_id != requester_id and user_id != requester_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only room creator or the member themselves can remove members"
            )
        
        success = await self.room_repo.remove_member(room_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove member from room"
            )
        
        updated_room = await self.room_repo.get_by_id(room_id)
        return ChatRoomResponse.model_validate(updated_room)
    
    async def create_message(self, message_data: ChatMessageCreate, sender_id: UUID) -> ChatMessageResponse:
        from sqlalchemy.orm import selectinload
        from app.db.models import ChatRoom
        
        room = await self.room_repo.get_by_id(
            message_data.room_id,
            options=[selectinload(ChatRoom.members)]
        )
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        user = await self.user_repo.get_by_id(sender_id)
        if user not in room.members:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this room"
            )
        
        message_dict = message_data.model_dump()
        message_dict["sender_id"] = sender_id
        
        message = await self.message_repo.create(message_dict)
        message = await self.message_repo.get_by_id(message.id)
        return ChatMessageResponse.model_validate(message)
    
    async def get_room_messages(self, room_id: int, skip: int = 0, limit: int = 100) -> List[ChatMessageResponse]:
        room = await self.room_repo.get_by_id(room_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        messages = await self.message_repo.get_room_messages(room_id, skip, limit)
        return [ChatMessageResponse.model_validate(msg) for msg in messages]
