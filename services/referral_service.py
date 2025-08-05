from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from repositories import UserRepository
from database.models import Referral, Order, OrderStatus
from database.database import async_session
from config import settings
import logging

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
    
    async def process_referral_reward(self, order_id: int) -> bool:
        """Обработать реферальную награду"""
        try:
            # Получаем заказ
            from repositories import OrderRepository
            order_repo = OrderRepository(self.session)
            order = await order_repo.get_by_id(order_id)
            
            if not order or order.status != OrderStatus.PAID.value:
                return False
            
            # Получаем пользователя
            user = await self.user_repo.get_by_telegram_id(order.user_id)
            if not user or not user.referrer_id:
                return False
            
            # Получаем реферера
            referrer = await self.user_repo.get_by_telegram_id(user.referrer_id)
            if not referrer:
                return False
            
            # Рассчитываем награду
            reward_percent = settings.REFERRAL_REWARD_PERCENT / 100
            reward_amount = order.total_price * reward_percent
            
            # Начисляем награду рефереру
            await self.user_repo.update_balance(referrer.id, reward_amount)
            
            # Обновляем статистику реферера
            await self.user_repo.update(
                referrer.id,
                referral_earnings=referrer.referral_earnings + reward_amount
            )
            
            # Создаем запись о реферальной награде
            referral = Referral(
                user_id=referrer.id,
                order_id=order.id,
                reward_amount=reward_amount,
                reward_percent=settings.REFERRAL_REWARD_PERCENT
            )
            
            self.session.add(referral)
            await self.session.commit()
            
            logger.info(f"Referral reward processed: {reward_amount}₽ for user {referrer.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing referral reward: {e}")
            await self.session.rollback()
            return False
    
    async def get_referral_stats(self, user_id: int) -> dict:
        """Получить статистику по рефералам"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return {}
        
        referrals = await self.user_repo.get_referrals(user_id)
        
        # Подсчитываем активных рефералов (с заказами)
        active_referrals = [r for r in referrals if r.total_orders > 0]
        
        return {
            "total_referrals": len(referrals),
            "active_referrals": len(active_referrals),
            "total_earnings": user.referral_earnings,
            "referral_code": user.referral_code
        }