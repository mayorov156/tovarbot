from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from repositories import OrderRepository, UserRepository, ProductRepository
from database.models import Order, OrderStatus, User, Product
from .referral_service import ReferralService
from .product_service import ProductService


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.user_repo = UserRepository(session)
        self.product_repo = ProductRepository(session)
        self.referral_service = ReferralService(session)
        self.product_service = ProductService(session)
    
    async def create_order(self, user_id: int, product_id: int, quantity: int = 1) -> tuple[Optional[Order], str]:
        """Создать заказ"""
        # Проверяем пользователя
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return None, "Пользователь не найден"
        
        # Проверяем товар
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            return None, "Товар не найден"
        
        # Проверяем доступность
        available, message = await self.product_service.check_product_availability(product_id, quantity)
        if not available:
            return None, message
        
        # Рассчитываем стоимость
        unit_price = product.price
        total_price = unit_price * quantity
        
        # Проверяем баланс
        if user.balance < total_price:
            return None, f"Недостаточно средств. Необходимо: {total_price}₽, на балансе: {user.balance}₽"
        
        # Резервируем товар
        if not await self.product_service.reserve_product(product_id, quantity):
            return None, "Не удалось зарезервировать товар"
        
        try:
            # Создаем заказ
            order = await self.order_repo.create(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                status=OrderStatus.PENDING.value
            )
            
            # Списываем средства
            await self.user_repo.update_balance(user_id, -total_price)
            
            # Обновляем статистику пользователя
            await self.user_repo.update(
                user_id,
                total_orders=user.total_orders + 1,
                total_spent=user.total_spent + total_price
            )
            
            return order, "Заказ успешно создан"
            
        except Exception as e:
            # Возвращаем товар в наличие в случае ошибки
            await self.product_service.return_product_stock(product_id, quantity)
            return None, f"Ошибка при создании заказа: {str(e)}"
    
    async def process_payment(self, order_id: int) -> tuple[bool, str]:
        """Обработать оплату заказа"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Заказ не найден"
        
        if order.status != OrderStatus.PENDING.value:
            return False, "Заказ уже обработан"
        
        # Обновляем статус
        await self.order_repo.update_status(order_id, OrderStatus.PAID)
        
        # Обрабатываем реферальную систему
        await self.referral_service.process_referral_reward(order_id)
        
        return True, "Оплата обработана"
    
    async def deliver_order(self, order_id: int, digital_content: str, admin_id: int) -> tuple[bool, str]:
        """Выдать заказ"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Заказ не найден"
        
        if order.status not in [OrderStatus.PENDING.value, OrderStatus.PAID.value]:
            return False, "Заказ нельзя выдать"
        
        # Обновляем статус и добавляем контент
        await self.order_repo.update_status(order_id, OrderStatus.DELIVERED, digital_content)
        
        # Увеличиваем счетчик продаж товара
        await self.product_repo.increment_sold(order.product_id, order.quantity)
        
        return True, "Заказ выдан"
    
    async def cancel_order(self, order_id: int, reason: str = "") -> tuple[bool, str]:
        """Отменить заказ"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return False, "Заказ не найден"
        
        if order.status == OrderStatus.DELIVERED.value:
            return False, "Выданный заказ нельзя отменить"
        
        if order.status == OrderStatus.CANCELLED.value:
            return False, "Заказ уже отменен"
        
        # Возвращаем товар в наличие
        await self.product_service.return_product_stock(order.product_id, order.quantity)
        
        # Возвращаем деньги пользователю
        await self.user_repo.update_balance(order.user_id, order.total_price)
        
        # Обновляем статус
        await self.order_repo.update_status(order_id, OrderStatus.CANCELLED)
        if reason:
            await self.order_repo.update(order_id, notes=reason)
        
        return True, "Заказ отменен"
    
    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Order]:
        """Получить заказы пользователя"""
        return await self.order_repo.get_user_orders(user_id, limit)
    
    async def get_pending_orders(self) -> List[Order]:
        """Получить заказы в ожидании"""
        return await self.order_repo.get_pending_orders()
    
    async def get_order_details(self, order_id: int) -> Optional[Order]:
        """Получить детали заказа"""
        return await self.order_repo.get_by_id(order_id)