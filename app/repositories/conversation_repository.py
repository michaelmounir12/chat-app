from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.repositories.base_repository import BaseRepository
from app.db.models import Conversation, User, ConversationType


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Conversation)

    async def get_with_participants(self, conversation_id: UUID) -> Optional[Conversation]:
        return await self.get_by_id(
            conversation_id,
            options=[selectinload(Conversation.participants)],
        )

    async def get_user_conversations(self, user_id: UUID) -> List[Conversation]:
        query = (
            select(Conversation)
            .where(Conversation.participants.any(id=user_id))
            .options(selectinload(Conversation.participants))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_direct_between(self, user_id_1: UUID, user_id_2: UUID) -> Optional[Conversation]:
        from sqlalchemy import func
        from app.db.models import conversation_participants

        sub = (
            select(conversation_participants.c.conversation_id)
            .where(conversation_participants.c.user_id.in_([user_id_1, user_id_2]))
            .group_by(conversation_participants.c.conversation_id)
            .having(func.count(conversation_participants.c.user_id) == 2)
        )
        query = (
            select(Conversation)
            .where(
                Conversation.id.in_(sub),
                Conversation.type == ConversationType.direct,
            )
            .options(selectinload(Conversation.participants))
        )
        result = await self.db.execute(query)
        convs = list(result.scalars().all())
        for c in convs:
            if len(c.participants) == 2 and {p.id for p in c.participants} == {user_id_1, user_id_2}:
                return c
        return None

    async def add_participant(self, conversation_id: UUID, user_id: UUID) -> bool:
        conv = await self.get_with_participants(conversation_id)
        if not conv:
            return False
        user = await self.db.get(User, user_id)
        if not user:
            return False
        if user in conv.participants:
            return True
        conv.participants.append(user)
        await self.db.flush()
        return True

    async def remove_participant(self, conversation_id: UUID, user_id: UUID) -> bool:
        conv = await self.get_with_participants(conversation_id)
        if not conv:
            return False
        user = await self.db.get(User, user_id)
        if not user:
            return False
        if user in conv.participants:
            conv.participants.remove(user)
            await self.db.flush()
        return True
