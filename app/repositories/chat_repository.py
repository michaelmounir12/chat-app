from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.repositories.base_repository import BaseRepository
from app.db.models import ChatRoom, ChatMessage, User


class ChatRoomRepository(BaseRepository[ChatRoom]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatRoom)
    
    async def get_by_name(self, name: str) -> Optional[ChatRoom]:
        query = select(ChatRoom).where(ChatRoom.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_rooms(self, user_id: int) -> List[ChatRoom]:
        query = (
            select(ChatRoom)
            .where(ChatRoom.members.any(id=user_id))
            .options(selectinload(ChatRoom.members))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def add_member(self, room_id: int, user_id: int) -> bool:
        room = await self.get_by_id(room_id, options=[selectinload(ChatRoom.members)])
        if not room:
            return False
        
        user = await self.db.get(User, user_id)
        if not user:
            return False
        
        if user not in room.members:
            room.members.append(user)
            await self.db.flush()
        return True
    
    async def remove_member(self, room_id: int, user_id: int) -> bool:
        room = await self.get_by_id(room_id, options=[selectinload(ChatRoom.members)])
        if not room:
            return False
        
        user = await self.db.get(User, user_id)
        if not user:
            return False
        
        if user in room.members:
            room.members.remove(user)
            await self.db.flush()
        return True


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ChatMessage)
    
    async def get_room_messages(
        self,
        room_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at.desc())
            .options(selectinload(ChatMessage.sender))
        )
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_messages(self, user_id: int, skip: int = 0, limit: int = 100) -> List[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.sender_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .options(selectinload(ChatMessage.sender), selectinload(ChatMessage.room))
        )
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
