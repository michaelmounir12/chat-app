from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.repositories.base_repository import BaseRepository
from app.db.models import MessageReadReceipt, Message


class ReadReceiptRepository(BaseRepository[MessageReadReceipt]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, MessageReadReceipt)

    async def create_receipt(self, message_id: UUID, user_id: UUID) -> MessageReadReceipt:
        existing = await self.get_by_message_and_user(message_id, user_id)
        if existing:
            return existing
        
        receipt = await self.create({
            "message_id": message_id,
            "user_id": user_id,
        })
        return receipt

    async def get_by_message_and_user(
        self, message_id: UUID, user_id: UUID
    ) -> Optional[MessageReadReceipt]:
        query = select(MessageReadReceipt).where(
            MessageReadReceipt.message_id == message_id,
            MessageReadReceipt.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_message(self, message_id: UUID) -> List[MessageReadReceipt]:
        query = (
            select(MessageReadReceipt)
            .where(MessageReadReceipt.message_id == message_id)
            .options(selectinload(MessageReadReceipt.user))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_conversation_and_user(
        self, conversation_id: UUID, user_id: UUID
    ) -> List[MessageReadReceipt]:
        query = (
            select(MessageReadReceipt)
            .join(Message)
            .where(
                Message.conversation_id == conversation_id,
                MessageReadReceipt.user_id == user_id,
            )
            .options(selectinload(MessageReadReceipt.message))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
