from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.repositories.base_repository import BaseRepository
from app.db.models import Message, MessageReadStatus


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Message)

    async def get_by_conversation(
        self,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .options(selectinload(Message.sender))
        )
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unread_for_user(self, conversation_id: UUID, user_id: UUID) -> List[Message]:
        query = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.read_status != MessageReadStatus.read,
            )
            .order_by(Message.created_at.asc())
            .options(selectinload(Message.sender))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_conversation_read_for_user(
        self, conversation_id: UUID, user_id: UUID
    ) -> int:
        from sqlalchemy import update
        query = (
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
            )
            .values(read_status=MessageReadStatus.read)
        )
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount or 0
