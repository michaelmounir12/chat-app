from typing import Dict, Set, Optional, Any
from uuid import UUID
import uuid as uuid_lib
import json
from fastapi import WebSocket
from app.websocket.redis_store import RedisConnectionStore


class ConnectionManager:
    """
    Manages WebSocket connections per conversation.
    In-memory store for local connections; Redis used for online users and connection metadata.
    """

    def __init__(self) -> None:
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        self._connection_meta: Dict[str, Dict[str, str]] = {}

    def _conversation_key(self, conversation_id: UUID) -> str:
        return str(conversation_id)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID,
        conversation_id: UUID,
    ) -> str:
        await websocket.accept()
        connection_id = f"{uuid_lib.uuid4()}"
        key = self._conversation_key(conversation_id)
        if key not in self._connections:
            self._connections[key] = {}
        self._connections[key][connection_id] = websocket
        self._connection_meta[connection_id] = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
        }
        await RedisConnectionStore.set_online(user_id, connection_id, conversation_id)
        return connection_id

    async def disconnect(
        self,
        connection_id: str,
        conversation_id: UUID,
    ) -> None:
        key = self._conversation_key(conversation_id)
        if key in self._connections:
            self._connections[key].pop(connection_id, None)
            if not self._connections[key]:
                del self._connections[key]
        meta = self._connection_meta.pop(connection_id, None)
        if meta:
            try:
                user_id = UUID(meta["user_id"])
                conv_id = UUID(meta["conversation_id"])
                await RedisConnectionStore.set_offline(user_id, connection_id, conv_id)
            except (ValueError, KeyError):
                pass

    def get_connection_ids_for_conversation(self, conversation_id: UUID) -> Set[str]:
        key = self._conversation_key(conversation_id)
        return set(self._connections.get(key, {}).keys())

    async def broadcast_to_conversation(
        self,
        conversation_id: UUID,
        message: Dict[str, Any],
        exclude_connection_id: Optional[str] = None,
    ) -> None:
        key = self._conversation_key(conversation_id)
        connections = self._connections.get(key, {})
        payload = json.dumps(message, default=str) if isinstance(message, dict) else message
        disconnected = []
        for cid, ws in connections.items():
            if cid == exclude_connection_id:
                continue
            try:
                await ws.send_text(payload if isinstance(payload, str) else json.dumps(payload))
            except Exception:
                disconnected.append(cid)
        for cid in disconnected:
            meta = self._connection_meta.get(cid)
            if meta and key == self._conversation_key(conversation_id):
                connections.pop(cid, None)
                self._connection_meta.pop(cid, None)

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        for conv_key, conns in self._connections.items():
            if connection_id in conns:
                try:
                    payload = json.dumps(message, default=str)
                    await conns[connection_id].send_text(payload)
                    return True
                except Exception:
                    return False
        return False

    async def send_to_user_in_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        message: Dict[str, Any],
    ) -> bool:
        key = self._conversation_key(conversation_id)
        connections = self._connections.get(key, {})
        uid_str = str(user_id)
        for cid, ws in connections.items():
            meta = self._connection_meta.get(cid)
            if meta and meta.get("user_id") == uid_str:
                try:
                    await ws.send_text(json.dumps(message, default=str))
                    return True
                except Exception:
                    pass
        return False
