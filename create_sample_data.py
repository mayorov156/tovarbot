"""
Скрипт для создания тестовых данных
"""
import asyncio
from database import init_db, get_session
from database.models import Category, Product


async def create_sample_data():
    """Создать тестовые данные"""
    await init_db()
    
    async for session in get_session():
        # Создаем категории
        categories_data = [
            {"name": "Игры", "description": "Игровые ключи и коды"},
            {"name": "Программы", "description": "Лицензии на программное обеспечение"},
            {"name": "Подписки", "description": "Подписки на различные сервисы"},
            {"name": "Курсы", "description": "Обучающие материалы и курсы"}
        ]
        
        categories = []
        for cat_data in categories_data:
            category = Category(**cat_data)
            session.add(category)
            categories.append(category)
        
        await session.commit()
        
        # Создаем товары
        products_data = [
            {
                "name": "Steam Ключ - Cyberpunk 2077",
                "description": "Ключ для активации игры Cyberpunk 2077 в Steam",
                "price": 1299.99,
                "category_id": 1,
                "stock_quantity": 5,
                "digital_content": "XXXXX-XXXXX-XXXXX"
            },
            {
                "name": "Origin Ключ - FIFA 24",
                "description": "Ключ для активации FIFA 24 в Origin",
                "price": 2999.99,
                "category_id": 1,
                "stock_quantity": 3,
                "digital_content": "YYYYY-YYYYY-YYYYY"
            },
            {
                "name": "Windows 11 Pro",
                "description": "Лицензионный ключ Windows 11 Professional",
                "price": 4999.99,
                "category_id": 2,
                "stock_quantity": 10,
                "digital_content": "ZZZZZ-ZZZZZ-ZZZZZ"
            },
            {
                "name": "Adobe Creative Cloud",
                "description": "Подписка Adobe Creative Cloud на 1 год",
                "price": 15999.99,
                "category_id": 3,
                "stock_quantity": 2,
                "is_unlimited": False
            },
            {
                "name": "Курс Python для начинающих",
                "description": "Полный курс изучения Python с нуля",
                "price": 2499.99,
                "category_id": 4,
                "is_unlimited": True,
                "digital_content": "Ссылка на курс: https://example.com/course"
            }
        ]
        
        for prod_data in products_data:
            product = Product(**prod_data)
            session.add(product)
        
        await session.commit()
        
        print("✅ Тестовые данные созданы успешно!")
        print(f"Создано категорий: {len(categories_data)}")
        print(f"Создано товаров: {len(products_data)}")


if __name__ == "__main__":
    asyncio.run(create_sample_data())