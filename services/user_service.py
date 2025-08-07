import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from repositories import UserRepository
from database.models import User
from config import settings


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
    
    async def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, 
                               first_name: Optional[str] = None, last_name: Optional[str] = None,
                               language_code: str = "ru") -> User:
        """Получить или создать пользователя"""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        
        if not user:
            # Генерируем уникальный реферальный код и промокод
            referral_code = self._generate_referral_code()
            promo_code = self._generate_promo_code()
            
            user = await self.user_repo.create(
                id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                referral_code=referral_code,
                promo_code=promo_code
            )
        else:
            # Обновляем информацию о пользователе
            updates = {}
            if username != user.username:
                updates['username'] = username
            if first_name != user.first_name:
                updates['first_name'] = first_name
            if last_name != user.last_name:
                updates['last_name'] = last_name
            
            # Генерируем промокод если его нет
            if not user.promo_code:
                updates['promo_code'] = self._generate_promo_code()
            
            if updates:
                await self.user_repo.update(user.id, **updates)
                # Обновляем объект пользователя
                user = await self.user_repo.get_by_telegram_id(telegram_id)
        
        return user
    
    async def set_referrer(self, user_id: int, referral_code: str) -> bool:
        """Установить реферера для пользователя"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user or user.referrer_id:
            return False
        
        referrer = await self.user_repo.get_by_referral_code(referral_code)
        if not referrer or referrer.id == user_id:
            return False
        
        await self.user_repo.update(user_id, referrer_id=referrer.id)
        return True
    
    async def add_balance(self, user_id: int, amount: float) -> Optional[User]:
        """Пополнить баланс пользователя"""
        if amount <= 0:
            return None
        
        return await self.user_repo.update_balance(user_id, amount)
    
    async def spend_balance(self, user_id: int, amount: float) -> bool:
        """Списать с баланса пользователя"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user or user.balance < amount:
            return False
        
        await self.user_repo.update_balance(user_id, -amount)
        return True
    
    async def get_user_info(self, user_id: int) -> Optional[dict]:
        """Получить информацию о пользователе"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return None
        
        referrals = await self.user_repo.get_referrals(user_id)
        
        return {
            "user": user,
            "referrals_count": len(referrals)
        }
    
    def _generate_referral_code(self) -> str:
        """Сгенерировать уникальный реферальный код"""
        return str(uuid.uuid4()).replace('-', '')[:8].upper()
    
    def _generate_promo_code(self) -> str:
        """Сгенерировать уникальный промокод"""
        return f"PROMO{str(uuid.uuid4()).replace('-', '')[:6].upper()}"
    
    async def get_user_brief_info(self, user_id: int) -> Optional[dict]:
        """Получить краткую информацию о пользователе для выдачи товара"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return None
        
        # Получаем статистику заказов
        orders = await self.user_repo.get_user_orders(user_id)
        total_orders = len(orders)
        total_spent = sum(order.total_price for order in orders)
        
        # Получаем последние заказы
        recent_orders = orders[:3] if orders else []
        
        # Формируем краткую информацию
        brief_info = {
            "user": user,
            "total_orders": total_orders,
            "total_spent": total_spent,
            "recent_orders": recent_orders,
            "has_orders": total_orders > 0,
            "is_active_buyer": total_orders >= 1,
            "is_regular_buyer": total_orders >= 3,
            "is_vip_buyer": total_orders >= 10 or total_spent >= 1000
        }
        
        return brief_info
    
    async def search_user_by_username(self, username: str) -> Optional[User]:
        """Найти пользователя по username"""
        if not username or not username.startswith('@'):
            return None
        
        # Убираем @ из username
        clean_username = username[1:] if username.startswith('@') else username
        
        return await self.user_repo.get_by_username(clean_username)
    
    async def search_user_by_id(self, user_id: int) -> Optional[User]:
        """Найти пользователя по ID"""
        return await self.user_repo.get_by_telegram_id(user_id)
    
    async def search_user_by_referral_code(self, referral_code: str) -> Optional[User]:
        """Найти пользователя по реферальному коду"""
        return await self.user_repo.get_by_referral_code(referral_code)
    
    async def search_user_by_promo_code(self, promo_code: str) -> Optional[User]:
        """Найти пользователя по промокоду"""
        return await self.user_repo.get_by_promo_code(promo_code)
    
    async def search_user_flexible(self, query: str) -> Optional[User]:
        """Гибкий поиск пользователя по различным параметрам"""
        if not query:
            return None
        
        # Пробуем найти по ID (если это число)
        try:
            user_id = int(query)
            user = await self.search_user_by_id(user_id)
            if user:
                return user
        except ValueError:
            pass
        
        # Пробуем найти по username
        if query.startswith('@'):
            user = await self.search_user_by_username(query)
            if user:
                return user
        
        # Пробуем найти по username без @
        user = await self.search_user_by_username(f"@{query}")
        if user:
            return user
        
        # Пробуем найти по реферальному коду
        user = await self.search_user_by_referral_code(query)
        if user:
            return user
        
        # Пробуем найти по промокоду
        user = await self.search_user_by_promo_code(query)
        if user:
            return user
        
        return None
    
    async def get_user_orders_summary(self, user_id: int) -> dict:
        """Получить сводку заказов пользователя"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return {
                "user_found": False,
                "message": "Пользователь не найден"
            }
        
        orders = await self.user_repo.get_user_orders(user_id)
        
        # Группируем заказы по статусу
        orders_by_status = {}
        for order in orders:
            status = order.status
            if status not in orders_by_status:
                orders_by_status[status] = []
            orders_by_status[status].append(order)
        
        # Статистика
        total_orders = len(orders)
        pending_orders = len(orders_by_status.get('pending', []))
        paid_orders = len(orders_by_status.get('paid', []))
        delivered_orders = len(orders_by_status.get('delivered', []))
        cancelled_orders = len(orders_by_status.get('cancelled', []))
        
        total_spent = sum(order.total_price for order in orders if order.status in ['paid', 'delivered'])
        
        return {
            "user_found": True,
            "user": user,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "paid_orders": paid_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_spent": total_spent,
            "orders_by_status": orders_by_status,
            "recent_orders": orders[:5] if orders else []
        }
    
    async def get_user_activity_level(self, user_id: int) -> str:
        """Определить уровень активности пользователя"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return "unknown"
        
        orders = await self.user_repo.get_user_orders(user_id)
        total_orders = len(orders)
        total_spent = sum(order.total_price for order in orders)
        
        # Определяем уровень активности
        if total_orders == 0:
            return "new"
        elif total_orders <= 2:
            return "occasional"
        elif total_orders <= 5:
            return "regular"
        elif total_orders <= 10:
            return "active"
        elif total_orders > 10 or total_spent > 1000:
            return "vip"
        else:
            return "regular"
    
    async def get_user_trust_score(self, user_id: int) -> dict:
        """Получить оценку доверия к пользователю"""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return {
                "score": 0,
                "level": "unknown",
                "factors": []
            }
        
        orders = await self.user_repo.get_user_orders(user_id)
        
        # Факторы для оценки доверия
        factors = []
        score = 0
        
        # Количество заказов
        total_orders = len(orders)
        if total_orders > 0:
            factors.append(f"Заказов: {total_orders}")
            score += min(total_orders * 10, 50)  # Максимум 50 баллов за заказы
        
        # Успешные заказы
        successful_orders = [o for o in orders if o.status in ['paid', 'delivered']]
        if successful_orders:
            factors.append(f"Успешных заказов: {len(successful_orders)}")
            score += len(successful_orders) * 5
        
        # Отмененные заказы (отрицательный фактор)
        cancelled_orders = [o for o in orders if o.status == 'cancelled']
        if cancelled_orders:
            factors.append(f"Отмененных заказов: {len(cancelled_orders)}")
            score -= len(cancelled_orders) * 10
        
        # Возраст аккаунта
        from datetime import datetime
        account_age_days = (datetime.now() - user.created_at).days
        if account_age_days > 30:
            factors.append(f"Аккаунт: {account_age_days} дней")
            score += min(account_age_days // 30, 20)  # Максимум 20 баллов за возраст
        
        # Определяем уровень доверия
        if score >= 80:
            level = "high"
        elif score >= 50:
            level = "medium"
        elif score >= 20:
            level = "low"
        else:
            level = "new"
        
        return {
            "score": max(0, score),
            "level": level,
            "factors": factors,
            "total_orders": total_orders,
            "successful_orders": len(successful_orders),
            "cancelled_orders": len(cancelled_orders),
            "account_age_days": account_age_days
        }