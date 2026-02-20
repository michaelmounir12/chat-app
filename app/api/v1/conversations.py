from typing import Annotated, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.services.conversation_service import ConversationService
from app.services.messaging_service import MessagingService
from app.websocket.redis_store import RedisConnectionStore
from app.schemas.messaging import (
    ConversationCreate,
    ConversationCreateDirect,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    PaginatedMessagesResponse,
    MessageReadReceiptResponse,
    TypingIndicatorRequest,
    TypingIndicatorResponse,
)

router = APIRouter()


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ConversationService(db)
    return await svc.list_user_conversations(user_id)


@router.get("/online", response_model=List[str])
async def list_online_user_ids(
    _: Annotated[UUID, Depends(get_current_user_id)],
):
    ids = await RedisConnectionStore.get_online_user_ids()
    return list(ids)


@router.get("/direct", response_model=ConversationResponse)
async def get_or_create_direct(
    other_user_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ConversationService(db)
    return await svc.get_or_create_direct(user_id, other_user_id)


@router.post("/direct", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_direct(
    body: ConversationCreateDirect,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ConversationService(db)
    return await svc.get_or_create_direct(user_id, body.other_user_id)


@router.post("/group", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: ConversationCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.db.models import ConversationType
    if body.type != ConversationType.group:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Use type=group for group conversations")
    svc = ConversationService(db)
    return await svc.create_group(user_id, body.name or "", body.participant_ids)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ConversationService(db)
    return await svc.get_conversation(conversation_id, user_id)


@router.get("/{conversation_id}/messages", response_model=PaginatedMessagesResponse)
async def get_messages(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[UUID] = Query(None),
    use_cache: bool = Query(True),
):
    svc = MessagingService(db)
    messages, next_cursor = await svc.get_conversation_messages(
        conversation_id, user_id, skip, limit, cursor, use_cache
    )
    return PaginatedMessagesResponse(
        messages=messages,
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message_rest(
    conversation_id: UUID,
    body: MessageCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from fastapi import HTTPException
    if str(body.conversation_id) != str(conversation_id):
        raise HTTPException(status_code=400, detail="conversation_id mismatch")
    svc = MessagingService(db)
    return await svc.send_message(user_id, body)


@router.post("/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_conversation_read(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MessagingService(db)
    await svc.mark_read(conversation_id, user_id)
    return None


@router.post("/messages/{message_id}/read", response_model=MessageReadReceiptResponse, status_code=status.HTTP_201_CREATED)
async def mark_message_read(
    message_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MessagingService(db)
    await svc.mark_message_read(message_id, user_id)
    from app.repositories.read_receipt_repository import ReadReceiptRepository
    from sqlalchemy.orm import selectinload
    from app.db.models import MessageReadReceipt
    receipt_repo = ReadReceiptRepository(db)
    receipt = await receipt_repo.get_by_message_and_user(message_id, user_id)
    if receipt:
        receipt = await receipt_repo.get_by_id(receipt.id, options=[selectinload(MessageReadReceipt.user)])
        return MessageReadReceiptResponse.model_validate(receipt)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Receipt not found")


@router.get("/messages/{message_id}/read-receipts", response_model=List[MessageReadReceiptResponse])
async def get_message_read_receipts(
    message_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.repositories.read_receipt_repository import ReadReceiptRepository
    from sqlalchemy.orm import selectinload
    from app.db.models import MessageReadReceipt
    receipt_repo = ReadReceiptRepository(db)
    receipts = await receipt_repo.get_by_message(message_id)
    return [MessageReadReceiptResponse.model_validate(r) for r in receipts]


@router.post("/{conversation_id}/typing", status_code=status.HTTP_204_NO_CONTENT)
async def send_typing_indicator(
    conversation_id: UUID,
    body: TypingIndicatorRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.repositories.user_repository import UserRepository
    from app.websocket.typing_indicator import TypingIndicatorManager
    from app.websocket.manager import ws_manager
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    
    await TypingIndicatorManager.set_typing(conversation_id, user_id, user.username, body.is_typing)
    
    typing_users = await TypingIndicatorManager.get_typing_users(conversation_id)
    payload = {
        "type": "typing_indicator",
        "conversation_id": str(conversation_id),
        "typing_users": [
            {
                "user_id": uid,
                "username": data.get("username", ""),
                "timestamp": data.get("timestamp", ""),
            }
            for uid, data in typing_users.items()
        ],
    }
    
    await ws_manager.broadcast_to_conversation(conversation_id, payload)
    return None


@router.get("/{conversation_id}/typing", response_model=List[TypingIndicatorResponse])
async def get_typing_indicators(
    conversation_id: UUID,
    _: Annotated[UUID, Depends(get_current_user_id)],
):
    from app.websocket.typing_indicator import TypingIndicatorManager
    from datetime import datetime
    
    typing_users = await TypingIndicatorManager.get_typing_users(conversation_id)
    return [
        TypingIndicatorResponse(
            user_id=UUID(uid),
            username=data.get("username", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            is_typing=True,
        )
        for uid, data in typing_users.items()
    ]
