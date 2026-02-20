from typing import Set, Optional
from uuid import UUID
import json
from app.db.redis_client import get_redis

ONLINE_USERS_KEY = "messaging:online_users"
USER_CONVERSATIONS_KEY = "messaging:user:{user_id}:conversations"
CONNECTION_KEY = "messaging:connection:{connection_id}"
CONNECTION_ID_PREFIX = "conn"
CONNECTION_IDS_KEY = "messaging:connection_ids"


class RedisConnectionStore:
    """Stores active WebSocket connections and online user state in Redis."""

    @staticmethod
    async def set_online(user_id: UUID, connection_id: str, conversation_id: UUID) -> None:
        redis = await get_redis()
        uid = str(user_id)
        cid = str(conversation_id)
        pipe = redis.pipeline()
        pipe.sadd(ONLINE_USERS_KEY, uid)
        pipe.sadd(USER_CONVERSATIONS_KEY.format(user_id=uid), cid)
        pipe.hset(CONNECTION_KEY.format(connection_id=connection_id), mapping={
            "user_id": uid,
            "conversation_id": cid,
        })
        pipe.expire(CONNECTION_KEY.format(connection_id=connection_id), 86400)
        await pipe.execute()

    @staticmethod
    async def set_offline(user_id: UUID, connection_id: str, conversation_id: UUID) -> None:
        redis = await get_redis()
        uid = str(user_id)
        cid = str(conversation_id)
        pipe = redis.pipeline()
        pipe.srem(USER_CONVERSATIONS_KEY.format(user_id=uid), cid)
        pipe.delete(CONNECTION_KEY.format(connection_id=connection_id))
        await pipe.execute()
        conversations = await redis.smembers(USER_CONVERSATIONS_KEY.format(user_id=uid))
        if not conversations:
            pipe2 = redis.pipeline()
            pipe2.srem(ONLINE_USERS_KEY, uid)
            await pipe2.execute()

    @staticmethod
    async def is_user_online(user_id: UUID) -> bool:
        redis = await get_redis()
        return await redis.sismember(ONLINE_USERS_KEY, str(user_id))

    @staticmethod
    async def get_online_user_ids() -> Set[str]:
        redis = await get_redis()
        members = await redis.smembers(ONLINE_USERS_KEY)
        return members or set()

    @staticmethod
    async def get_connection_info(connection_id: str) -> Optional[dict]:
        redis = await get_redis()
        data = await redis.hgetall(CONNECTION_KEY.format(connection_id=connection_id))
        if not data:
            return None
        return data

    @staticmethod
    async def get_user_conversations(user_id: UUID) -> Set[str]:
        redis = await get_redis()
        members = await redis.smembers(USER_CONVERSATIONS_KEY.format(user_id=str(user_id)))
        return members or set()
