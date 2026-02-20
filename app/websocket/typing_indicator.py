from typing import Dict, Optional
from uuid import UUID
from datetime import datetime, timezone
from app.db.redis_client import get_redis
import json

TYPING_KEY_PREFIX = "typing:conversation:"
TYPING_TTL = 10


class TypingIndicatorManager:
    @staticmethod
    async def set_typing(
        conversation_id: UUID,
        user_id: UUID,
        username: str,
        is_typing: bool = True
    ) -> None:
        redis = await get_redis()
        key = f"{TYPING_KEY_PREFIX}{conversation_id}"
        
        if is_typing:
            data = {
                "user_id": str(user_id),
                "username": username,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await redis.hset(key, str(user_id), json.dumps(data))
            await redis.expire(key, TYPING_TTL)
        else:
            await redis.hdel(key, str(user_id))
            if await redis.hlen(key) == 0:
                await redis.delete(key)

    @staticmethod
    async def get_typing_users(conversation_id: UUID) -> Dict[str, dict]:
        redis = await get_redis()
        key = f"{TYPING_KEY_PREFIX}{conversation_id}"
        data = await redis.hgetall(key)
        
        result = {}
        for user_id_str, value_str in data.items():
            try:
                result[user_id_str] = json.loads(value_str)
            except (json.JSONDecodeError, TypeError):
                continue
        
        return result

    @staticmethod
    async def clear_typing(conversation_id: UUID, user_id: UUID) -> None:
        await TypingIndicatorManager.set_typing(conversation_id, user_id, "", False)
