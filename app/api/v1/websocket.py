from typing import Dict, Set, Optional
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.security import verify_token
from app.db.redis_client import get_redis
from app.repositories.user_repository import UserRepository
from app.db.session import AsyncSessionLocal
import json
import redis.asyncio as redis

router = APIRouter()

active_connections: Dict[int, Set[WebSocket]] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID, room_id: int):
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        
        self.active_connections[room_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].discard(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast_to_room(self, message: dict, room_id: int, exclude_websocket: WebSocket = None):
        if room_id not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[room_id]:
            try:
                if connection != exclude_websocket:
                    await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        for connection in disconnected:
            self.active_connections[room_id].discard(connection)


manager = ConnectionManager()


async def get_user_from_token(token: str) -> Optional[UUID]:
    payload = verify_token(token)
    if payload is None:
        return None
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None
    
    try:
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except (ValueError, TypeError):
        return None
    
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if user is None:
            return None
    
    return user_id


@router.websocket("/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(...)
):
    user_id = await get_user_from_token(token)
    
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await manager.connect(websocket, user_id, room_id)
    
    redis_client = await get_redis()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message = {
                "type": "message",
                "room_id": room_id,
                "sender_id": user_id,
                "content": message_data.get("content", ""),
                "timestamp": message_data.get("timestamp")
            }
            
            await redis_client.publish(f"chat:room:{room_id}", json.dumps(message))
            await manager.broadcast_to_room(message, room_id, exclude_websocket=websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
    except Exception as e:
        manager.disconnect(websocket, room_id)
        raise
