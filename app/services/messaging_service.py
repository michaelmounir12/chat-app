from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.db.models import MessageReadStatus, Message
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.messaging import MessageCreate, MessageResponse


class MessagingService:
    def __init__(self, db: AsyncSession):
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)

    async def send_message(self, sender_id: UUID, data: MessageCreate) -> MessageResponse:
        conv = await self.conv_repo.get_with_participants(data.conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        participant_ids = {p.id for p in conv.participants}
        if sender_id not in participant_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant",
            )
        msg = await self.msg_repo.create({
            "sender_id": sender_id,
            "conversation_id": data.conversation_id,
            "content": data.content,
            "read_status": MessageReadStatus.sent,
        })
        msg = await self.msg_repo.get_by_id(msg.id, options=[selectinload(Message.sender)])
        return MessageResponse.model_validate(msg)

    async def get_message_with_sender(self, message_id: UUID) -> Optional[MessageResponse]:
        msg = await self.msg_repo.get_by_id(message_id, options=[selectinload(Message.sender)])
        if not msg:
            return None
        return MessageResponse.model_validate(msg)

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[MessageResponse]:
        conv = await self.conv_repo.get_with_participants(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        if user_id not in {p.id for p in conv.participants}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant",
            )
        messages = await self.msg_repo.get_by_conversation(conversation_id, skip, limit)
        return [MessageResponse.model_validate(m) for m in messages]

    async def get_offline_messages(self, conversation_id: UUID, user_id: UUID) -> List[MessageResponse]:
        messages = await self.msg_repo.get_unread_for_user(conversation_id, user_id)
        return [MessageResponse.model_validate(m) for m in messages]

    async def mark_read(self, conversation_id: UUID, user_id: UUID) -> int:
        conv = await self.conv_repo.get_with_participants(conversation_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        if user_id not in {p.id for p in conv.participants}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant",
            )
        return await self.msg_repo.mark_conversation_read_for_user(conversation_id, user_id)
