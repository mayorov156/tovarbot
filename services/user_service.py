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