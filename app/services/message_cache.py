from typing import List, Optional
from uuid import UUID
from app.db.redis_client import get_redis
import json
from datetime import datetime

MESSAGE_CACHE_KEY = "messages:conversation:{conversation_id}"
CACHE_SIZE = 50
CACHE_TTL = 3600


class MessageCacheService:
    @staticmethod
    async def cache_message(conversation_id: UUID, message_data: dict) -> None:
        redis = await get_redis()
        key = MESSAGE_CACHE_KEY.format(conversation_id=str(conversation_id))
        
        message_json = json.dumps(message_data, default=str)
        await redis.lpush(key, message_json)
        await redis.ltrim(key, 0, CACHE_SIZE - 1)
        await redis.expire(key, CACHE_TTL)

    @staticmethod
    async def get_cached_messages(
        conversation_id: UUID,
        limit: int = CACHE_SIZE
    ) -> List[dict]:
        redis = await get_redis()
        key = MESSAGE_CACHE_KEY.format(conversation_id=str(conversation_id))
        
        messages_json = await redis.lrange(key, 0, limit - 1)
        messages = []
        
        for msg_json in messages_json:
            try:
                msg = json.loads(msg_json)
                messages.append(msg)
            except (json.JSONDecodeError, TypeError):
                continue
        
        return messages

    @staticmethod
    async def invalidate_cache(conversation_id: UUID) -> None:
        redis = await get_redis()
        key = MESSAGE_CACHE_KEY.format(conversation_id=str(conversation_id))
        await redis.delete(key)

    @staticmethod
    async def cache_messages_batch(conversation_id: UUID, messages: List[dict]) -> None:
        redis = await get_redis()
        key = MESSAGE_CACHE_KEY.format(conversation_id=str(conversation_id))
        
        pipe = redis.pipeline()
        for msg in messages:
            msg_json = json.dumps(msg, default=str)
            pipe.lpush(key, msg_json)
        
        pipe.ltrim(key, 0, CACHE_SIZE - 1)
        pipe.expire(key, CACHE_TTL)
        await pipe.execute()
