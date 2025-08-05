from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from database.models import Product, Category
from .base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)
    
    async def get_active_products(self, category_id: Optional[int] = None, limit: Optional[int] = None) -> List[Product]:
        """Получить активные товары"""
        stmt = select(Product).options(selectinload(Product.category)).where(Product.is_active == True)
        
        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        
        stmt = stmt.order_by(Product.sort_order, Product.name)
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_available_products(self, category_id: Optional[int] = None) -> List[Product]:
        """Получить доступные товары (в наличии)"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(
                and_(
                    Product.is_active == True,
                    or_(
                        Product.is_unlimited == True,
                        Product.stock_quantity > 0
                    )
                )
            )
        )
        
        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        
        stmt = stmt.order_by(Product.sort_order, Product.name)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_products(self, query: str) -> List[Product]:
        """Поиск товаров по названию"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(
                and_(
                    Product.is_active == True,
                    Product.name.ilike(f"%{query}%")
                )
            )
            .order_by(Product.name)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """Обновить остатки товара"""
        product = await self.get_by_id(product_id)
        if product and not product.is_unlimited:
            product.stock_quantity += quantity_change
            if product.stock_quantity < 0:
                product.stock_quantity = 0
            await self.session.commit()
            await self.session.refresh(product)
        return product
    
    async def increment_sold(self, product_id: int, quantity: int = 1) -> Optional[Product]:
        """Увеличить счетчик продаж"""
        product = await self.get_by_id(product_id)
        if product:
            product.total_sold += quantity
            await self.session.commit()
            await self.session.refresh(product)
        return product
    
    async def get_low_stock_products(self, threshold: int = 5) -> List[Product]:
        """Получить товары с низкими остатками"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(
                and_(
                    Product.is_active == True,
                    Product.is_unlimited == False,
                    Product.stock_quantity <= threshold
                )
            )
            .order_by(Product.stock_quantity)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_top_selling(self, limit: int = 10) -> List[Product]:
        """Получить топ продаваемых товаров"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.total_sold > 0)
            .order_by(Product.total_sold.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())