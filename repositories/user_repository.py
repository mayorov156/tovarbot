from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database.models import User
from .base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        stmt = select(User).where(User.id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_or_create_user(self, telegram_id: int, **user_data) -> User:
        """Получить или создать пользователя"""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            user_data['id'] = telegram_id
            user = await self.create(**user_data)
        return user
    
    async def get_by_referral_code(self, referral_code: str) -> Optional[User]:
        """Получить пользователя по реферальному коду"""
        stmt = select(User).where(User.referral_code == referral_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_balance(self, user_id: int, amount: float) -> Optional[User]:
        """Обновить баланс пользователя"""
        user = await self.get_by_telegram_id(user_id)
        if user:
            user.balance += amount
            await self.session.commit()
            await self.session.refresh(user)
        return user
    
    async def get_referrals(self, user_id: int) -> List[User]:
        """Получить рефералов пользователя"""
        stmt = select(User).where(User.referrer_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_top_buyers(self, limit: int = 10) -> List[User]:
        """Получить топ покупателей"""
        stmt = (
            select(User)
            .where(User.total_spent > 0)
            .order_by(User.total_spent.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_stats(self) -> dict:
        """Получить статистику пользователей"""
        total_users = await self.session.scalar(select(func.count(User.id)))
        active_users = await self.session.scalar(
            select(func.count(User.id)).where(User.total_orders > 0)
        )
        total_balance = await self.session.scalar(select(func.sum(User.balance))) or 0
        
        return {
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "total_balance": total_balance
        }