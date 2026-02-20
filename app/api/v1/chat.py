from typing import Annotated, List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user_id
from app.services.chat_service import ChatService
from app.schemas.chat import (
    ChatRoomCreate,
    ChatRoomUpdate,
    ChatRoomResponse,
    ChatMessageCreate,
    ChatMessageResponse
)

router = APIRouter()


@router.post("/rooms", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: ChatRoomCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.create_room(room_data, user_id)


@router.get("/rooms", response_model=List[ChatRoomResponse])
async def get_my_rooms(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.get_user_rooms(user_id)


@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
async def get_room(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.get_room_by_id(room_id)


@router.put("/rooms/{room_id}", response_model=ChatRoomResponse)
async def update_room(
    room_id: int,
    room_data: ChatRoomUpdate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.update_room(room_id, room_data, user_id)


@router.post("/rooms/{room_id}/members/{member_id}", response_model=ChatRoomResponse)
async def add_member_to_room(
    room_id: int,
    member_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.add_member_to_room(room_id, member_id, user_id)


@router.delete("/rooms/{room_id}/members/{member_id}", response_model=ChatRoomResponse)
async def remove_member_from_room(
    room_id: int,
    member_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.remove_member_from_room(room_id, member_id, user_id)


@router.post("/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: ChatMessageCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.create_message(message_data, user_id)


@router.get("/rooms/{room_id}/messages", response_model=List[ChatMessageResponse])
async def get_room_messages(
    room_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_service = ChatService(db)
    return await chat_service.get_room_messages(room_id, skip, limit)
