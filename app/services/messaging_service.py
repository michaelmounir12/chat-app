from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.db.models import MessageReadStatus, Message
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.read_receipt_repository import ReadReceiptRepository
from app.services.message_cache import MessageCacheService
from app.schemas.messaging import MessageCreate, MessageResponse


class MessagingService:
    def __init__(self, db: AsyncSession):
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)
        self.receipt_repo = ReadReceiptRepository(db)

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
        
        cache_data = {
            "id": str(msg.id),
            "sender_id": str(msg.sender_id),
            "conversation_id": str(msg.conversation_id),
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "read_status": msg.read_status.value,
        }
        if msg.sender:
            cache_data["sender"] = {
                "id": str(msg.sender.id),
                "username": msg.sender.username,
                "email": msg.sender.email,
            }
        await MessageCacheService.cache_message(data.conversation_id, cache_data)
        
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
        cursor: Optional[UUID] = None,
        use_cache: bool = True,
    ) -> Tuple[List[MessageResponse], Optional[UUID]]:
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
        
        if use_cache and skip == 0 and cursor is None:
            cached = await MessageCacheService.get_cached_messages(conversation_id, limit)
            if cached:
                from app.schemas.messaging import MessageResponse
                from app.db.models import MessageReadStatus
                messages = []
                for c in cached:
                    try:
                        msg = MessageResponse(
                            id=UUID(c["id"]),
                            sender_id=UUID(c["sender_id"]),
                            conversation_id=UUID(c["conversation_id"]),
                            content=c["content"],
                            created_at=datetime.fromisoformat(c["created_at"]),
                            read_status=MessageReadStatus(c["read_status"]),
                        )
                        messages.append(msg)
                    except (KeyError, ValueError, TypeError):
                        continue
                if messages:
                    next_cursor = messages[-1].id if len(messages) == limit else None
                    return messages, next_cursor
        
        if cursor:
            from sqlalchemy import select
            cursor_msg = await self.msg_repo.get_by_id(cursor)
            if cursor_msg:
                messages = await self.msg_repo.get_by_conversation_after(
                    conversation_id, cursor_msg.created_at, limit
                )
            else:
                messages = await self.msg_repo.get_by_conversation(conversation_id, 0, limit)
        else:
            messages = await self.msg_repo.get_by_conversation(conversation_id, skip, limit)
        
        result = [MessageResponse.model_validate(m) for m in messages]
        next_cursor = result[-1].id if result and len(result) == limit else None
        return result, next_cursor

    async def mark_message_read(self, message_id: UUID, user_id: UUID) -> bool:
        msg = await self.msg_repo.get_by_id(message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )
        conv = await self.conv_repo.get_with_participants(msg.conversation_id)
        if user_id not in {p.id for p in conv.participants}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant",
            )
        if msg.sender_id == user_id:
            return False
        
        await self.receipt_repo.create_receipt(message_id, user_id)
        return True

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
