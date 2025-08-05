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
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID (алиас для get_by_telegram_id)"""
        return await self.get_by_telegram_id(user_id)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по username (точное совпадение)"""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_username_icase(self, username: str) -> Optional[User]:
        """Получить пользователя по username без учета регистра"""
        stmt = select(User).where(func.lower(User.username) == func.lower(username))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search_users_by_username(self, username_pattern: str) -> List[User]:
        """Поиск пользователей по частичному совпадению username"""
        stmt = select(User).where(
            func.lower(User.username).contains(func.lower(username_pattern))
        ).limit(10)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
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
    
    async def get_recent_users(self, limit: int = 10) -> List[User]:
        """Получить недавно зарегистрированных пользователей"""
        from datetime import datetime, timedelta
        
        # Пользователи за последние 7 дней
        recent_date = datetime.now() - timedelta(days=7)
        
        stmt = (
            select(User)
            .where(User.created_at >= recent_date)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_users(self, limit: int = 10) -> List[User]:
        """Получить наиболее активных пользователей (по количеству заказов)"""
        stmt = (
            select(User)
            .where(User.total_orders > 0)
            .order_by(User.total_orders.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_users_with_balance(self, limit: int = 10) -> List[User]:
        """Получить пользователей с наибольшим балансом"""
        stmt = (
            select(User)
            .where(User.balance > 0)
            .order_by(User.balance.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())