from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.models import ConversationType
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.messaging import ConversationCreate, ConversationResponse


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.conv_repo = ConversationRepository(db)
        self.user_repo = UserRepository(db)

    async def get_or_create_direct(self, user_id: UUID, other_user_id: UUID) -> ConversationResponse:
        if user_id == other_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create direct conversation with yourself",
            )
        other = await self.user_repo.get_by_id(other_user_id)
        if not other:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        existing = await self.conv_repo.get_direct_between(user_id, other_user_id)
        if existing:
            return ConversationResponse.model_validate(existing)
        conv = await self.conv_repo.create({
            "type": ConversationType.direct,
            "name": None,
        })
        await self.conv_repo.add_participant(conv.id, user_id)
        await self.conv_repo.add_participant(conv.id, other_user_id)
        conv = await self.conv_repo.get_with_participants(conv.id)
        return ConversationResponse.model_validate(conv)

    async def create_group(self, user_id: UUID, name: str, participant_ids: List[UUID]) -> ConversationResponse:
        if user_id not in participant_ids:
            participant_ids = [user_id] + list(participant_ids)
        conv = await self.conv_repo.create({
            "type": ConversationType.group,
            "name": name or None,
        })
        for pid in participant_ids:
            user = await self.user_repo.get_by_id(pid)
            if user:
                await self.conv_repo.add_participant(conv.id, pid)
        conv = await self.conv_repo.get_with_participants(conv.id)
        return ConversationResponse.model_validate(conv)

    async def get_conversation(self, conversation_id: UUID, user_id: UUID) -> ConversationResponse:
        conv = await self.conv_repo.get_with_participants(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        participant_ids = {p.id for p in conv.participants}
        if user_id not in participant_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant",
            )
        return ConversationResponse.model_validate(conv)

    async def list_user_conversations(self, user_id: UUID) -> List[ConversationResponse]:
        convs = await self.conv_repo.get_user_conversations(user_id)
        return [ConversationResponse.model_validate(c) for c in convs]
