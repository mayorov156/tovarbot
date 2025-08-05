from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from repositories import ProductRepository, CategoryRepository
from database.models import Product, Category


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
    
    async def get_categories_menu(self) -> List[Category]:
        """Получить категории для меню"""
        return await self.category_repo.get_active_categories()
    
    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """Получить товары по категории"""
        return await self.product_repo.get_available_products(category_id)
    
    async def get_product_details(self, product_id: int) -> Optional[Product]:
        """Получить детальную информацию о товаре"""
        product = await self.product_repo.get_by_id(product_id)
        
        if not product or not product.is_active:
            return None
        
        # Проверяем доступность товара
        if not product.is_unlimited and product.stock_quantity <= 0:
            return None
        
        return product
    
    async def search_products(self, query: str) -> List[Product]:
        """Поиск товаров"""
        if len(query) < 2:
            return []
        
        return await self.product_repo.search_products(query)
    
    async def check_product_availability(self, product_id: int, quantity: int = 1) -> tuple[bool, str]:
        """Проверить доступность товара для покупки"""
        product = await self.product_repo.get_by_id(product_id)
        
        if not product:
            return False, "Товар не найден"
        
        if not product.is_active:
            return False, "Товар недоступен"
        
        if not product.is_unlimited and product.stock_quantity < quantity:
            return False, f"Недостаточно товара в наличии. Доступно: {product.stock_quantity}"
        
        return True, "Товар доступен"
    
    async def reserve_product(self, product_id: int, quantity: int = 1) -> bool:
        """Зарезервировать товар (уменьшить остаток)"""
        available, message = await self.check_product_availability(product_id, quantity)
        
        if not available:
            return False
        
        # Уменьшаем остаток только для ограниченных товаров
        product = await self.product_repo.get_by_id(product_id)
        if product and not product.is_unlimited:
            await self.product_repo.update_stock(product_id, -quantity)
        
        return True
    
    async def return_product_stock(self, product_id: int, quantity: int = 1) -> bool:
        """Вернуть товар в наличие (увеличить остаток)"""
        product = await self.product_repo.get_by_id(product_id)
        if product and not product.is_unlimited:
            await self.product_repo.update_stock(product_id, quantity)
            return True
        return False
    
    async def get_popular_products(self, limit: int = 5) -> List[Product]:
        """Получить популярные товары"""
        return await self.product_repo.get_top_selling(limit)
    
    async def get_low_stock_alert(self, threshold: int = 5) -> List[Product]:
        """Получить товары с низкими остатками"""
        return await self.product_repo.get_low_stock_products(threshold)