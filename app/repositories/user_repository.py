from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base_repository import BaseRepository
from app.db.models import User


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, id: UUID) -> Optional[User]:
        return await super().get_by_id(id)
    
    async def email_exists(self, email: str) -> bool:
        user = await self.get_by_email(email)
        return user is not None
    
    async def username_exists(self, username: str) -> bool:
        user = await self.get_by_username(username)
        return user is not None
