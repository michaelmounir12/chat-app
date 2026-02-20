from typing import Annotated, List
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


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    svc = MessagingService(db)
    return await svc.get_conversation_messages(conversation_id, user_id, skip, limit)


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
