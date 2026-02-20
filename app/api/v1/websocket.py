from typing import Optional
from uuid import UUID
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.security import verify_token
from app.db.session import AsyncSessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.websocket.manager import ConnectionManager
from app.services.messaging_service import MessagingService
from app.schemas.messaging import MessageCreate

router = APIRouter()
ws_manager = ConnectionManager()


async def get_user_id_from_token(token: str) -> Optional[UUID]:
    payload = verify_token(token)
    if payload is None:
        return None
    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None
    try:
        return UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except (ValueError, TypeError):
        return None


@router.websocket("/conversations/{conversation_id}")
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str = Query(..., alias="token"),
):
    user_id = await get_user_id_from_token(token)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as db:
        conv_repo = ConversationRepository(db)
        conv = await conv_repo.get_with_participants(conversation_id)
        if not conv:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        if user_id not in {p.id for p in conv.participants}:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    connection_id = await ws_manager.connect(websocket, user_id, conversation_id)

    try:
        async with AsyncSessionLocal() as db:
            messaging = MessagingService(db)
            offline = await messaging.get_offline_messages(conversation_id, user_id)
            for msg in offline:
                payload = {
                    "type": "offline_message",
                    "id": str(msg.id),
                    "sender_id": str(msg.sender_id),
                    "conversation_id": str(msg.conversation_id),
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "read_status": msg.read_status.value if hasattr(msg.read_status, "value") else str(msg.read_status),
                }
                if msg.sender:
                    payload["sender"] = {"id": str(msg.sender.id), "username": msg.sender.username, "email": msg.sender.email}
                await ws_manager.send_to_connection(connection_id, payload)
            await messaging.mark_read(conversation_id, user_id)
            await db.commit()

        async with AsyncSessionLocal() as db:
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            username = user.username if user else "Unknown"

        while True:
            data = await websocket.receive_text()
            try:
                body = json.loads(data)
            except json.JSONDecodeError:
                continue
            
            event_type = body.get("type", "message")
            
            if event_type == "typing":
                from app.websocket.typing_indicator import TypingIndicatorManager
                is_typing = body.get("is_typing", True)
                await TypingIndicatorManager.set_typing(conversation_id, user_id, username, is_typing)
                
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
                continue
            
            content = (body.get("content") or "").strip()
            if not content:
                continue

            async with AsyncSessionLocal() as db:
                from app.core.rate_limit import RateLimiter
                allowed, retry_after = await RateLimiter.check_user_rate_limit(
                    user_id, "send_message", 30, 60
                )
                if not allowed:
                    error_payload = {
                        "type": "error",
                        "message": f"Rate limit exceeded. Retry after {retry_after} seconds",
                        "retry_after": retry_after,
                    }
                    await ws_manager.send_to_connection(connection_id, error_payload)
                    continue
                
                messaging = MessagingService(db)
                try:
                    msg = await messaging.send_message(
                        user_id,
                        MessageCreate(conversation_id=conversation_id, content=content),
                    )
                    await db.commit()
                except Exception:
                    await db.rollback()
                    continue

            payload = {
                "type": "message",
                "id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "conversation_id": str(msg.conversation_id),
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "read_status": msg.read_status.value if hasattr(msg.read_status, "value") else str(msg.read_status),
            }
            if msg.sender:
                payload["sender"] = {"id": str(msg.sender.id), "username": msg.sender.username, "email": msg.sender.email}

            await ws_manager.broadcast_to_conversation(
                conversation_id,
                payload,
                exclude_connection_id=connection_id,
            )
            await ws_manager.send_to_connection(connection_id, payload)

    except WebSocketDisconnect:
        from app.websocket.typing_indicator import TypingIndicatorManager
        await TypingIndicatorManager.clear_typing(conversation_id, user_id)
        await ws_manager.disconnect(connection_id, conversation_id)
    except Exception:
        from app.websocket.typing_indicator import TypingIndicatorManager
        await TypingIndicatorManager.clear_typing(conversation_id, user_id)
        await ws_manager.disconnect(connection_id, conversation_id)
        raise
