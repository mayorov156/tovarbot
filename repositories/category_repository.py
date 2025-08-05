from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database.models import Category, Product
from .base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Category)
    
    async def get_active_categories(self) -> List[Category]:
        """Получить активные категории"""
        stmt = (
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.name)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_categories_with_products(self) -> List[Category]:
        """Получить категории с товарами"""
        stmt = (
            select(Category)
            .options(selectinload(Category.products))
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.name)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_name(self, name: str) -> Optional[Category]:
        """Получить категорию по названию"""
        stmt = select(Category).where(Category.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_categories_stats(self) -> List[dict]:
        """Получить статистику по категориям"""
        stmt = (
            select(
                Category.id,
                Category.name,
                func.count(Product.id).label('products_count'),
                func.sum(Product.stock_quantity).label('total_stock'),
                func.sum(Product.total_sold).label('total_sold')
            )
            .outerjoin(Product)
            .where(Category.is_active == True)
            .group_by(Category.id, Category.name)
            .order_by(Category.sort_order, Category.name)
        )
        
        result = await self.session.execute(stmt)
        return [
            {
                "id": row.id,
                "name": row.name, 
                "products_count": row.products_count or 0,
                "total_stock": row.total_stock or 0,
                "total_sold": row.total_sold or 0
            }
            for row in result.all()
        ]