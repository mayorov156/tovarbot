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
    
    async def get_by_promo_code(self, promo_code: str) -> Optional[User]:
        """Получить пользователя по промокоду"""
        stmt = select(User).where(User.promo_code == promo_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_orders(self, user_id: int) -> List:
        """Получить заказы пользователя"""
        from database.models import Order
        
        stmt = (
            select(Order)
            .options(selectinload(Order.product))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_users_flexible(self, query: str, limit: int = 10) -> List[User]:
        """Гибкий поиск пользователей по различным параметрам"""
        users = []
        
        # Поиск по username (частичное совпадение)
        username_users = await self.search_users_by_username(query)
        users.extend(username_users)
        
        # Поиск по реферальному коду
        if len(query) >= 6:  # Минимальная длина реферального кода
            referral_user = await self.get_by_referral_code(query)
            if referral_user and referral_user not in users:
                users.append(referral_user)
        
        # Поиск по промокоду
        if query.startswith('PROMO'):
            promo_user = await self.get_by_promo_code(query)
            if promo_user and promo_user not in users:
                users.append(promo_user)
        
        # Пробуем найти по ID (если это число)
        try:
            user_id = int(query)
            id_user = await self.get_by_telegram_id(user_id)
            if id_user and id_user not in users:
                users.append(id_user)
        except ValueError:
            pass
        
        return users[:limit]
    
    async def get_user_statistics(self, user_id: int) -> dict:
        """Получить статистику пользователя"""
        from database.models import Order
        
        # Общая статистика заказов
        total_orders = await self.session.scalar(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        ) or 0
        
        # Статистика по статусам
        pending_orders = await self.session.scalar(
            select(func.count(Order.id))
            .where(Order.user_id == user_id, Order.status == 'pending')
        ) or 0
        
        paid_orders = await self.session.scalar(
            select(func.count(Order.id))
            .where(Order.user_id == user_id, Order.status == 'paid')
        ) or 0
        
        delivered_orders = await self.session.scalar(
            select(func.count(Order.id))
            .where(Order.user_id == user_id, Order.status == 'delivered')
        ) or 0
        
        cancelled_orders = await self.session.scalar(
            select(func.count(Order.id))
            .where(Order.user_id == user_id, Order.status == 'cancelled')
        ) or 0
        
        # Общая сумма потраченная
        total_spent = await self.session.scalar(
            select(func.sum(Order.total_price))
            .where(Order.user_id == user_id, Order.status.in_(['paid', 'delivered']))
        ) or 0
        
        return {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "paid_orders": paid_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_spent": total_spent
        }
    
    async def get_recent_user_orders(self, user_id: int, limit: int = 5) -> List:
        """Получить последние заказы пользователя"""
        from database.models import Order
        
        stmt = (
            select(Order)
            .options(selectinload(Order.product))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_users_by_activity_level(self, level: str, limit: int = 10) -> List[User]:
        """Получить пользователей по уровню активности"""
        if level == "new":
            stmt = (
                select(User)
                .where(User.total_orders == 0)
                .order_by(User.created_at.desc())
                .limit(limit)
            )
        elif level == "occasional":
            stmt = (
                select(User)
                .where(User.total_orders.between(1, 2))
                .order_by(User.total_orders.desc())
                .limit(limit)
            )
        elif level == "regular":
            stmt = (
                select(User)
                .where(User.total_orders.between(3, 5))
                .order_by(User.total_orders.desc())
                .limit(limit)
            )
        elif level == "active":
            stmt = (
                select(User)
                .where(User.total_orders.between(6, 10))
                .order_by(User.total_orders.desc())
                .limit(limit)
            )
        elif level == "vip":
            stmt = (
                select(User)
                .where(
                    (User.total_orders > 10) | (User.total_spent > 1000)
                )
                .order_by(User.total_spent.desc())
                .limit(limit)
            )
        else:
            return []
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())