from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from database.database import Base

T = TypeVar('T', bound=Base)


class BaseRepository(ABC, Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model
    
    async def create(self, **kwargs) -> T:
        """Создать новую запись"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Получить запись по ID"""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Получить все записи"""
        stmt = select(self.model).offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Обновить запись"""
        stmt = update(self.model).where(self.model.id == id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удалить запись"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def count(self) -> int:
        """Подсчитать количество записей"""
        stmt = select(func.count(self.model.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0