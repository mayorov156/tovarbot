from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from database.models import Order, OrderStatus
from .base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)
    
    async def get_user_orders(self, user_id: int, limit: Optional[int] = None) -> List[Order]:
        """Получить заказы пользователя"""
        stmt = (
            select(Order)
            .options(selectinload(Order.product), selectinload(Order.user))
            .where(Order.user_id == user_id)
            .order_by(desc(Order.created_at))
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_pending_orders(self) -> List[Order]:
        """Получить заказы в ожидании"""
        stmt = (
            select(Order)
            .options(selectinload(Order.product), selectinload(Order.user))
            .where(Order.status == OrderStatus.PENDING.value)
            .order_by(Order.created_at)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Получить заказы по статусу"""
        stmt = (
            select(Order)
            .options(selectinload(Order.product), selectinload(Order.user))
            .where(Order.status == status.value)
            .order_by(desc(Order.created_at))
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_status(self, order_id: int, status: OrderStatus, delivered_content: Optional[str] = None) -> Optional[Order]:
        """Обновить статус заказа"""
        order = await self.get_by_id(order_id)
        if order:
            order.status = status.value
            if status == OrderStatus.DELIVERED and delivered_content:
                order.delivered_content = delivered_content
                order.delivered_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(order)
        return order
    
    async def get_orders_stats(self, days: int = 30) -> dict:
        """Получить статистику заказов"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Общая статистика
        total_orders = await self.session.scalar(select(func.count(Order.id)))
        
        # Статистика за период
        period_orders = await self.session.scalar(
            select(func.count(Order.id)).where(Order.created_at >= since_date)
        )
        
        # Выручка за период
        period_revenue = await self.session.scalar(
            select(func.sum(Order.total_price)).where(
                and_(
                    Order.created_at >= since_date,
                    Order.status.in_([OrderStatus.PAID.value, OrderStatus.DELIVERED.value])
                )
            )
        ) or 0
        
        # Заказы по статусам
        pending_count = await self.session.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING.value)
        )
        
        paid_count = await self.session.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PAID.value)
        )
        
        delivered_count = await self.session.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED.value)
        )
        
        return {
            "total_orders": total_orders or 0,
            "period_orders": period_orders or 0,
            "period_revenue": period_revenue,
            "pending_orders": pending_count or 0,
            "paid_orders": paid_count or 0,
            "delivered_orders": delivered_count or 0,
            "days": days
        }
    
    async def get_recent_orders(self, limit: int = 10) -> List[Order]:
        """Получить последние заказы"""
        stmt = (
            select(Order)
            .options(selectinload(Order.product), selectinload(Order.user))
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())