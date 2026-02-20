from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from app.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)
IdType = Union[int, UUID]


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model
    
    async def get_by_id(self, id: IdType, options: Optional[List] = None) -> Optional[ModelType]:
        query = select(self.model).where(self.model.id == id)
        
        if options:
            for option in options:
                query = query.options(option)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        options: Optional[List] = None
    ) -> List[ModelType]:
        query = select(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        if options:
            for option in options:
                query = query.options(option)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: IdType, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        query = update(self.model).where(self.model.id == id).values(**obj_in).returning(self.model)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.scalar_one_or_none()
    
    async def delete(self, id: IdType) -> bool:
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount > 0
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
        
        result = await self.db.execute(query)
        return result.scalar_one() or 0
