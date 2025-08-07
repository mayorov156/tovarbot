"""Сервис для работы со складом товаров"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from database.models import Product, Category, User, WarehouseLog, ProductType
from repositories.product_repository import ProductRepository
from repositories.category_repository import CategoryRepository
from repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)


class WarehouseService:
    """Сервис для управления складом"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
        self.user_repo = UserRepository(session)
    
    async def add_product(
        self,
        name: str,
        category_id: int,
        product_type: str,
        duration: str,
        content: str,
        price: float,
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Optional[Product]:
        """Добавить новый товар на склад"""
        try:
            # Создаем товар
            product = Product(
                name=name,
                category_id=category_id,
                product_type=product_type,
                duration=duration,
                digital_content=content,
                price=price,
                stock_quantity=1,
                is_active=True
            )
            
            self.session.add(product)
            await self.session.flush()  # Получаем ID продукта
            
            # Логируем добавление
            await self._log_warehouse_action(
                product_id=product.id,
                admin_id=admin_id,
                admin_username=admin_username,
                action="add_product",
                quantity=1,
                description=f"Добавлен товар: {name} ({product_type})"
            )
            
            await self.session.commit()
            
            # Перезагружаем товар с отношениями
            await self.session.refresh(product)
            stmt = select(Product).options(selectinload(Product.category)).where(Product.id == product.id)
            result = await self.session.execute(stmt)
            product = result.scalar_one()
            
            logger.info(f"WAREHOUSE: Added product '{name}' (ID: {product.id}) by admin {admin_id}")
            return product
            
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            await self.session.rollback()
            return None
    
    async def give_product(
        self,
        product_id: int,
        recipient_id: int,
        recipient_username: Optional[str],
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Product]]:
        """
        Выдать товар пользователю
        
        Returns:
            (success, content, updated_product)
        """
        try:
            # Получаем товар с категорией
            product = await self.get_product_with_category(product_id)
            if not product:
                return False, None, None
            
            # Проверяем наличие
            if not product.is_unlimited and product.stock_quantity <= 0:
                return False, None, None
            
            # Получаем содержимое товара
            content = product.digital_content
            if not content:
                return False, None, None
            
            # Уменьшаем остаток (если товар не безлимитный)
            if not product.is_unlimited:
                product.stock_quantity -= 1
            
            # Увеличиваем счетчик продаж
            product.total_sold += 1
            
            # Логируем выдачу
            await self._log_warehouse_action(
                product_id=product_id,
                admin_id=admin_id,
                admin_username=admin_username,
                recipient_id=recipient_id,
                recipient_username=recipient_username,
                action="give_product",
                quantity=1,
                delivered_content=content,
                description=f"Выдан товар: {product.name}"
            )
            
            await self.session.commit()
            await self.session.refresh(product)
            
            logger.info(
                f"WAREHOUSE: Admin {admin_id} gave product '{product.name}' "
                f"to user {recipient_id} (@{recipient_username})"
            )
            
            return True, content, product
            
        except Exception as e:
            logger.error(f"Error giving product: {e}")
            await self.session.rollback()
            return False, None, None
    
    async def get_available_products(self) -> List[Product]:
        """Получить товары доступные для выдачи"""
        return await self.product_repo.get_available_products()
    
    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """Получить доступные товары по категории (только с остатками > 0 или безлимитные)"""
        return await self.product_repo.get_available_products(category_id)
    
    async def get_categories(self) -> List[Category]:
        """Получить все активные категории"""
        return await self.category_repo.get_active_categories()
    
    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Получить категорию по ID"""
        return await self.category_repo.get_by_id(category_id)
    
    async def find_user_by_username_or_id(self, identifier: str) -> Optional[User]:
        """Улучшенный поиск пользователя по username или ID с множественными стратегиями"""
        try:
            # Нормализуем ввод
            normalized = self.normalize_user_input(identifier)
            
            if not normalized:
                logger.warning(f"WAREHOUSE: Empty identifier after normalization: '{identifier}'")
                return None
            
            # Стратегия 1: Пробуем как Telegram ID (только цифры)
            if normalized.isdigit():
                user_id = int(normalized)
                user = await self.user_repo.get_by_id(user_id)
                if user:
                    logger.info(f"WAREHOUSE: Found user by Telegram ID {user_id}: @{user.username or 'no_username'}")
                    return user
                else:
                    logger.info(f"WAREHOUSE: User with ID {user_id} not found, trying as username...")
                    # Не возвращаем None сразу, продолжаем поиск как username
            
            # Стратегия 2: Точное совпадение по username (с учетом регистра)
            user = await self.user_repo.get_by_username(normalized)
            if user:
                logger.info(f"WAREHOUSE: Found user by exact username '{normalized}': ID {user.id}")
                return user
            
            # Стратегия 3: Поиск без учета регистра
            user = await self.user_repo.get_by_username_icase(normalized)
            if user:
                logger.info(f"WAREHOUSE: Found user by case-insensitive username '{normalized}': @{user.username} (ID {user.id})")
                return user
            
            # Стратегия 4: Поиск по частичному совпадению username
            users = await self.user_repo.search_users_by_username(normalized)
            if users:
                # Если найдено несколько, предпочитаем точное совпадение
                for user in users:
                    if user.username and user.username.lower() == normalized.lower():
                        logger.info(f"WAREHOUSE: Found user by partial search exact match '{normalized}': @{user.username} (ID {user.id})")
                        return user
                
                # Если точного совпадения нет, берем первого найденного
                user = users[0]
                logger.info(f"WAREHOUSE: Found user by partial username search '{normalized}': @{user.username} (ID {user.id})")
                return user
            
            # Стратегия 5: Поиск по first_name для случаев, когда нет username
            if not normalized.isdigit():
                from sqlalchemy import select, func
                stmt = select(User).where(
                    func.lower(User.first_name).contains(func.lower(normalized))
                ).limit(5)
                result = await self.session.execute(stmt)
                users_by_name = list(result.scalars().all())
                
                if users_by_name:
                    user = users_by_name[0]
                    logger.info(f"WAREHOUSE: Found user by first_name search '{normalized}': {user.first_name} (ID {user.id})")
                    return user
            
            logger.warning(f"WAREHOUSE: User not found by any strategy for identifier: '{identifier}' (normalized: '{normalized}')")
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by identifier '{identifier}': {e}")
            return None
    
    def normalize_user_input(self, user_input: str) -> str:
        """Нормализация пользовательского ввода для поиска"""
        if not user_input:
            return ""
        
        # Убираем лишние пробелы
        normalized = user_input.strip()
        
        # Убираем @ в начале
        if normalized.startswith('@'):
            normalized = normalized[1:]
        
        # Убираем внутренние пробелы и спецсимволы
        normalized = ''.join(char for char in normalized if char.isalnum() or char in ['_'])
        
        return normalized
    
    async def validate_product_data(
        self,
        name: str,
        category_id: int,
        product_type: str,
        duration: str,
        content: str,
        price: float
    ) -> Tuple[bool, Optional[str]]:
        """Валидировать данные товара"""
        
        # Проверяем имя
        if not name or len(name.strip()) < 3:
            return False, "Название товара должно содержать минимум 3 символа"
        
        # Проверяем категорию
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            return False, "Категория не найдена"
        
        # Проверяем тип товара
        valid_types = [t.value for t in ProductType]
        if product_type not in valid_types:
            return False, "Неверный тип товара"
        
        # Проверяем длительность
        if not duration or len(duration.strip()) < 1:
            return False, "Длительность не может быть пустой"
        
        # Проверяем содержимое
        if not content or len(content.strip()) < 1:
            return False, "Содержимое товара не может быть пустым"
        
        # Проверяем формат содержимого для аккаунтов
        if product_type == ProductType.ACCOUNT.value:
            if ":" not in content:
                return False, "Для аккаунта используйте формат 'логин:пароль'"
        
        # Проверяем цену
        if price <= 0:
            return False, "Цена должна быть больше 0"
        
        if price > 100000:
            return False, "Цена не может превышать 100,000₽"
        
        return True, None
    
    async def _log_warehouse_action(
        self,
        product_id: int,
        admin_id: int,
        action: str,
        quantity: int = 1,
        admin_username: Optional[str] = None,
        recipient_id: Optional[int] = None,
        recipient_username: Optional[str] = None,
        delivered_content: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Записать действие в лог склада"""
        log_entry = WarehouseLog(
            product_id=product_id,
            admin_id=admin_id,
            admin_username=admin_username,
            recipient_id=recipient_id,
            recipient_username=recipient_username,
            action=action,
            quantity=quantity,
            delivered_content=delivered_content,
            description=description
        )
        
        self.session.add(log_entry)
    
    async def get_warehouse_history(self, limit: int = 50) -> List[WarehouseLog]:
        """Получить историю действий на складе"""
        stmt = (
            select(WarehouseLog)
            .options(selectinload(WarehouseLog.product))
            .order_by(WarehouseLog.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_product_with_category(self, product_id: int) -> Optional[Product]:
        """Получить товар с загруженной категорией"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_products(self) -> List[Product]:
        """Получить все активные товары с категориями"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.is_active == True)
            .order_by(Product.name)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_products_with_stock(self) -> List[Product]:
        """Получить все товары с остатками (включая безлимитные)"""
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
            .order_by(Product.name)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_products_out_of_stock(self) -> List[Product]:
        """Получить все товары без остатков (не безлимитные и с остатками = 0)"""
        stmt = (
            select(Product)
            .options(selectinload(Product.category))
            .where(
                and_(
                    Product.is_active == True,
                    Product.is_unlimited == False,
                    Product.stock_quantity <= 0
                )
            )
            .order_by(Product.name)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_category(
        self,
        name: str,
        description: Optional[str],
        manual_url: Optional[str],
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Optional[Category]:
        """Создать новую категорию"""
        try:
            # Проверяем, существует ли категория с таким именем
            existing = await self.category_repo.get_by_name(name)
            if existing:
                return None
            
            # Создаем категорию
            category = Category(
                name=name,
                description=description or "",
                manual_url=manual_url,
                is_active=True,
                sort_order=0
            )
            
            self.session.add(category)
            await self.session.flush()
            
            # Логируем создание
            await self._log_warehouse_action(
                product_id=0,  # Для категорий используем 0
                admin_id=admin_id,
                admin_username=admin_username,
                action="create_category",
                quantity=1,
                description=f"Создана категория: {name}" + (f" с мануалом: {manual_url}" if manual_url else "")
            )
            
            await self.session.commit()
            await self.session.refresh(category)
            
            logger.info(f"WAREHOUSE: Created category '{name}' (ID: {category.id}) by admin {admin_id}" + (f" with manual: {manual_url}" if manual_url else ""))
            return category
            
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            await self.session.rollback()
            return None
    
    async def validate_category_data(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Валидировать данные категории"""
        
        # Проверяем имя
        if not name or len(name.strip()) < 2:
            return False, "Название категории должно содержать минимум 2 символа"
        
        # Проверяем уникальность имени
        existing = await self.category_repo.get_by_name(name.strip())
        if existing:
            return False, "Категория с таким названием уже существует"
        
        return True, None
    
    async def has_categories(self) -> bool:
        """Проверить, есть ли хотя бы одна категория"""
        categories = await self.get_categories()
        return len(categories) > 0
    
    async def mass_add_products(
        self,
        base_name: str,
        category_id: int,
        product_type: str,
        duration: str,
        price: float,
        content_lines: List[str],
        admin_id: int,
        admin_username: Optional[str] = None
    ) -> Tuple[List[Product], dict]:
        """
        Массовое добавление товаров с валидацией и отчетом
        
        Returns:
            (products, report) где report содержит статистику ошибок
        """
        try:
            products = []
            report = {
                'total_lines': len(content_lines),
                'successful': 0,
                'errors': [],
                'duplicates': 0,
                'empty_lines': 0,
                'invalid_format': 0
            }
            
            # Проверяем дубли в самом наборе данных
            unique_contents = set()
            processed_contents = []
            
            for i, content in enumerate(content_lines, 1):
                content = content.strip()
                
                if not content:
                    report['empty_lines'] += 1
                    report['errors'].append(f"Строка {i}: пустая строка")
                    continue
                
                # Проверяем формат содержимого
                if product_type == ProductType.ACCOUNT.value:
                    # Используем улучшенную валидацию для аккаунтов
                    parsed_lines = self.parse_content_lines(content, product_type)
                    if not parsed_lines or parsed_lines[0] != content:
                        # Пробуем нормализовать формат
                        normalized_content = self._normalize_account_content(content)
                        if not normalized_content:
                            report['invalid_format'] += 1
                            report['errors'].append(f"Строка {i}: неверный формат (ожидается логин:пароль или логин|пароль)")
                            continue
                        else:
                            content = normalized_content  # Используем нормализованную версию
                
                # Проверяем дубли в текущем наборе
                if content.lower() in unique_contents:
                    report['duplicates'] += 1
                    report['errors'].append(f"Строка {i}: дубликат контента")
                    continue
                
                unique_contents.add(content.lower())
                
                # Проверяем дубли в базе данных
                existing_product = await self._check_content_duplicate(content, product_type)
                if existing_product:
                    report['duplicates'] += 1
                    report['errors'].append(f"Строка {i}: товар с таким содержимым уже существует (ID: {existing_product.id})")
                    continue
                
                processed_contents.append((i, content))
            
            # Создаем товары только для валидных строк
            for line_num, content in processed_contents:
                # Генерируем название с номером
                product_name = f"{base_name} #{line_num}"
                
                # Создаем товар
                product = Product(
                    name=product_name,
                    description=f"Автоматически добавлен через массовое добавление",
                    price=price,
                    category_id=category_id,
                    is_active=True,
                    is_unlimited=False,
                    stock_quantity=1,
                    total_sold=0,
                    product_type=product_type,
                    duration=duration,
                    digital_content=content
                )
                
                self.session.add(product)
                products.append(product)
            
            # Сохраняем все товары
            if products:
                await self.session.flush()
                
                # Логируем массовое добавление
                for product in products:
                    await self._log_warehouse_action(
                        product_id=product.id,
                        admin_id=admin_id,
                        admin_username=admin_username,
                        action="mass_add_product",
                        quantity=1,
                        description=f"Массовое добавление: {product.name}"
                    )
                
                await self.session.commit()
                
                # Обновляем объекты после коммита
                for product in products:
                    await self.session.refresh(product)
            
            report['successful'] = len(products)
            
            logger.info(f"WAREHOUSE: Mass added {len(products)} products by admin {admin_id}. "
                       f"Errors: {len(report['errors'])}, Duplicates: {report['duplicates']}")
            
            return products, report
            
        except Exception as e:
            logger.error(f"Error in mass add products: {e}")
            await self.session.rollback()
            report = {
                'total_lines': len(content_lines),
                'successful': 0,
                'errors': [f"Критическая ошибка: {str(e)}"],
                'duplicates': 0,
                'empty_lines': 0,
                'invalid_format': 0
            }
            return [], report
    
    def parse_content_lines(self, content_text: str, product_type: str) -> List[str]:
        """Парсинг строк контента в зависимости от типа товара с улучшенной поддержкой форматов"""
        lines = [line.strip() for line in content_text.split('\n') if line.strip()]
        
        # Проверяем формат в зависимости от типа
        if product_type == ProductType.ACCOUNT.value:
            # Для аккаунтов поддерживаем различные форматы разделителей
            valid_lines = []
            for line in lines:
                # Попробуем различные разделители: :, |, ;, tab, двойной пробел
                separators = [':', '|', ';', '\t', '  ']
                normalized_line = None
                
                for separator in separators:
                    if separator in line:
                        parts = [part.strip() for part in line.split(separator) if part.strip()]
                        if len(parts) >= 2:
                            # Берем первые две части как логин:пароль, остальное игнорируем
                            normalized_line = f"{parts[0]}:{parts[1]}"
                            break
                
                # Если не нашли разделители, но есть пробелы
                if not normalized_line and ' ' in line:
                    parts = [part.strip() for part in line.split() if part.strip()]
                    if len(parts) >= 2:
                        # Берем первые две части
                        normalized_line = f"{parts[0]}:{parts[1]}"
                
                if normalized_line:
                    valid_lines.append(normalized_line)
                elif ':' in line:  # Оставляем старую логику как fallback
                    valid_lines.append(line)
                    
            return valid_lines
        else:
            # Для ключей и промокодов просто возвращаем строки
            return lines
    
    def parse_quick_add_data(self, data_text: str) -> Tuple[bool, dict]:
        """Парсинг данных для быстрого добавления товара"""
        try:
            lines = [line.strip() for line in data_text.split('\n') if line.strip()]
            
            if len(lines) < 5:
                return False, {"error": "Недостаточно данных. Требуется минимум 5 строк."}
            
            result = {}
            
            # Первая строка - название
            result['name'] = lines[0]
            
            # Ищем остальные поля
            for line in lines[1:]:
                if line.lower().startswith('тип:'):
                    type_value = line.split(':', 1)[1].strip().lower()
                    if type_value in ['аккаунт', 'account']:
                        result['product_type'] = ProductType.ACCOUNT.value
                    elif type_value in ['ключ', 'key']:
                        result['product_type'] = ProductType.KEY.value
                    elif type_value in ['промокод', 'promo']:
                        result['product_type'] = ProductType.PROMO.value
                    else:
                        return False, {"error": f"Неизвестный тип товара: {type_value}"}
                
                elif line.lower().startswith('длительность:'):
                    result['duration'] = line.split(':', 1)[1].strip()
                
                elif line.lower().startswith('цена:'):
                    try:
                        price_str = line.split(':', 1)[1].strip()
                        result['price'] = float(price_str)
                    except ValueError:
                        return False, {"error": f"Неверная цена: {price_str}"}
                
                elif line.lower().startswith('контент:'):
                    result['content'] = line.split(':', 1)[1].strip()
            
            # Проверяем наличие всех обязательных полей
            required_fields = ['name', 'product_type', 'duration', 'price', 'content']
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                return False, {"error": f"Не хватает полей: {', '.join(missing_fields)}"}
            
            # Валидируем контент в зависимости от типа
            if result['product_type'] == ProductType.ACCOUNT.value:
                if ':' not in result['content']:
                    return False, {"error": "Для аккаунтов контент должен быть в формате логин:пароль"}
            
            return True, result
            
        except Exception as e:
            return False, {"error": f"Ошибка парсинга: {str(e)}"}
    
    def _normalize_account_content(self, content: str) -> Optional[str]:
        """Нормализовать содержимое аккаунта к формату логин:пароль"""
        try:
            # Попробуем различные разделители
            separators = [':', '|', ';', '\t', '  ']
            
            for separator in separators:
                if separator in content:
                    parts = [part.strip() for part in content.split(separator) if part.strip()]
                    if len(parts) >= 2 and parts[0] and parts[1]:
                        return f"{parts[0]}:{parts[1]}"
            
            # Если не нашли разделители, попробуем пробелы
            if ' ' in content:
                parts = [part.strip() for part in content.split() if part.strip()]
                if len(parts) >= 2 and parts[0] and parts[1]:
                    return f"{parts[0]}:{parts[1]}"
            
            return None
            
        except Exception:
            return None

    async def _check_content_duplicate(self, content: str, product_type: str) -> Optional[Product]:
        """Проверить, существует ли товар с таким же содержимым"""
        try:
            stmt = (
                select(Product)
                .where(
                    and_(
                        Product.digital_content == content,
                        Product.product_type == product_type,
                        Product.is_active == True
                    )
                )
            )
            
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error checking content duplicate: {e}")
            return None
    
    async def update_product(
        self,
        product_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        product_type: Optional[str] = None,
        duration: Optional[str] = None,
        digital_content: Optional[str] = None,
        admin_id: int = None,
        admin_username: Optional[str] = None
    ) -> Optional[Product]:
        """Обновить товар"""
        try:
            product = await self.get_product_with_category(product_id)
            if not product:
                return None
            
            # Сохраняем старые значения для логирования
            old_values = {
                'name': product.name,
                'price': product.price,
                'product_type': product.product_type,
                'duration': product.duration,
                'digital_content': product.digital_content
            }
            
            # Обновляем только переданные поля
            if name is not None:
                product.name = name
            if description is not None:
                product.description = description  
            if price is not None:
                product.price = price
            if product_type is not None:
                product.product_type = product_type
            if duration is not None:
                product.duration = duration
            if digital_content is not None:
                product.digital_content = digital_content
            
            # Логируем изменения
            changes = []
            for field, old_value in old_values.items():
                new_value = getattr(product, field)
                if old_value != new_value:
                    changes.append(f"{field}: '{old_value}' -> '{new_value}'")
            
            if changes:
                await self._log_warehouse_action(
                    product_id=product_id,
                    admin_id=admin_id,
                    admin_username=admin_username,
                    action="edit_product",
                    quantity=1,
                    description=f"Изменения: {'; '.join(changes)}"
                )
            
            await self.session.commit()
            await self.session.refresh(product)
            
            logger.info(f"WAREHOUSE: Product {product_id} updated by admin {admin_id}. Changes: {changes}")
            return product
            
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            await self.session.rollback()
            return None
    
    async def get_category_stats(self) -> List[dict]:
        """Получить статистику ДОСТУПНЫХ товаров по категориям (только с остатками > 0 или безлимитные)"""
        from sqlalchemy import func
        try:
            # Получаем все категории с подсчетом ДОСТУПНЫХ товаров (с остатками > 0 или безлимитные)
            stmt = select(
                Category.id,
                Category.name,
                select(func.count(Product.id)).where(
                    and_(
                        Product.category_id == Category.id,
                        Product.is_active == True,
                        or_(
                            Product.is_unlimited == True,
                            Product.stock_quantity > 0
                        )
                    )
                ).label('total_products'),
                select(func.sum(Product.stock_quantity)).where(
                    and_(
                        Product.category_id == Category.id,
                        Product.is_active == True,
                        Product.is_unlimited == False
                    )
                ).label('total_stock')
            ).order_by(Category.name)
            
            result = await self.session.execute(stmt)
            category_stats = []
            
            for row in result:
                # Получаем количество безлимитных товаров
                unlimited_stmt = select(func.count(Product.id)).where(
                    and_(
                        Product.category_id == row.id,
                        Product.is_active == True,
                        Product.is_unlimited == True
                    )
                )
                unlimited_result = await self.session.execute(unlimited_stmt)
                unlimited_count = unlimited_result.scalar() or 0
                
                # Анализируем дубликаты по названиям в категории
                duplicates_info = await self._analyze_category_duplicates(row.id)
                
                category_stats.append({
                    'id': row.id,
                    'name': row.name,
                    'total_products': row.total_products or 0,
                    'total_stock': row.total_stock or 0,
                    'unlimited_products': unlimited_count,
                    'duplicates_info': duplicates_info
                })
            
            return category_stats
            
        except Exception as e:
            logger.error(f"Error getting category stats: {e}")
            return []
    
    async def get_single_category_stats(self, category_id: int) -> Optional[dict]:
        """Получить статистику для одной конкретной категории в реальном времени"""
        from sqlalchemy import func
        try:
            # Получаем категорию
            category = await self.get_category_by_id(category_id)
            if not category:
                return None
            
            # Получаем количество доступных товаров
            available_products_stmt = select(func.count(Product.id)).where(
                and_(
                    Product.category_id == category_id,
                    Product.is_active == True,
                    or_(
                        Product.is_unlimited == True,
                        Product.stock_quantity > 0
                    )
                )
            )
            available_result = await self.session.execute(available_products_stmt)
            available_count = available_result.scalar() or 0
            
            # Получаем общий остаток (только для товаров с ограниченным количеством)
            total_stock_stmt = select(func.sum(Product.stock_quantity)).where(
                and_(
                    Product.category_id == category_id,
                    Product.is_active == True,
                    Product.is_unlimited == False
                )
            )
            stock_result = await self.session.execute(total_stock_stmt)
            total_stock = stock_result.scalar() or 0
            
            # Получаем количество безлимитных товаров
            unlimited_stmt = select(func.count(Product.id)).where(
                and_(
                    Product.category_id == category_id,
                    Product.is_active == True,
                    Product.is_unlimited == True
                )
            )
            unlimited_result = await self.session.execute(unlimited_stmt)
            unlimited_count = unlimited_result.scalar() or 0
            
            return {
                'id': category.id,
                'name': category.name,
                'total_products': available_count,
                'total_stock': total_stock,
                'unlimited_products': unlimited_count
            }
            
        except Exception as e:
            logger.error(f"Error getting single category stats for category {category_id}: {e}")
            return None

    async def _analyze_category_duplicates(self, category_id: int) -> dict:
        """Анализировать дубликаты товаров в категории по названиям"""
        try:
            from sqlalchemy import func, text
            
            # Получаем все товары в категории
            stmt = select(Product).where(
                and_(
                    Product.category_id == category_id,
                    Product.is_active == True
                )
            ).order_by(Product.name, Product.id)
            
            result = await self.session.execute(stmt)
            products = list(result.scalars().all())
            
            # Группируем по нормализованным названиям
            grouped_products = {}
            for product in products:
                # Нормализуем название (убираем номера, лишние пробелы)
                normalized_name = self._normalize_product_name(product.name)
                
                if normalized_name not in grouped_products:
                    grouped_products[normalized_name] = {
                        'original_name': product.name,
                        'products': [],
                        'total_stock': 0,
                        'has_unlimited': False
                    }
                
                group = grouped_products[normalized_name]
                group['products'].append({
                    'id': product.id,
                    'name': product.name,
                    'stock': product.stock_quantity,
                    'is_unlimited': product.is_unlimited,
                    'price': product.price
                })
                
                if product.is_unlimited:
                    group['has_unlimited'] = True
                else:
                    group['total_stock'] += product.stock_quantity
            
            # Находим "переполненные" (дублирующиеся) товары
            overflow_products = {}
            for normalized_name, group in grouped_products.items():
                if len(group['products']) > 1:  # Есть дубликаты
                    overflow_products[normalized_name] = {
                        'original_name': group['original_name'],
                        'count': len(group['products']),
                        'total_stock': group['total_stock'],
                        'has_unlimited': group['has_unlimited'],
                        'products': group['products']
                    }
            
            return {
                'total_unique_names': len(grouped_products),
                'overflow_count': len(overflow_products),
                'overflow_products': overflow_products
            }
            
        except Exception as e:
            logger.error(f"Error analyzing duplicates for category {category_id}: {e}")
            return {'total_unique_names': 0, 'overflow_count': 0, 'overflow_products': {}}

    def _normalize_product_name(self, name: str) -> str:
        """Нормализовать название товара для поиска дубликатов"""
        import re
        
        # Убираем номера в конце названия типа "#1", "#2", "№1"
        normalized = re.sub(r'\s*[#№]\d+\s*$', '', name.strip())
        
        # Убираем лишние пробелы и приводим к нижнему регистру
        normalized = ' '.join(normalized.split()).lower()
        
        return normalized

    async def get_smart_warehouse_stats(self) -> dict:
        """Получить умную статистику склада с анализом переполненных товаров"""
        try:
            category_stats = await self.get_category_stats()
            
            # Общая статистика
            total_categories = len(category_stats)
            total_products = sum(cat['total_products'] for cat in category_stats)
            total_stock = sum(cat['total_stock'] for cat in category_stats)
            total_unlimited = sum(cat['unlimited_products'] for cat in category_stats)
            
            # Анализируем переполненные товары
            overflow_categories = []
            total_overflow_products = 0
            
            for category in category_stats:
                duplicates = category['duplicates_info']
                if duplicates['overflow_count'] > 0:
                    overflow_categories.append({
                        'category_name': category['name'],
                        'overflow_count': duplicates['overflow_count'],
                        'overflow_products': duplicates['overflow_products']
                    })
                    total_overflow_products += duplicates['overflow_count']
            
            # Находим самые переполненные товары
            top_overflow = []
            for category in overflow_categories:
                for name, info in category['overflow_products'].items():
                    top_overflow.append({
                        'category': category['category_name'],
                        'name': info['original_name'],
                        'count': info['count'],
                        'total_stock': info['total_stock'],
                        'has_unlimited': info['has_unlimited'],
                        'products': info['products']
                    })
            
            # Сортируем по количеству дубликатов
            top_overflow.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'general': {
                    'total_categories': total_categories,
                    'total_products': total_products,
                    'total_stock': total_stock,
                    'total_unlimited': total_unlimited
                },
                'overflow': {
                    'categories_with_overflow': len(overflow_categories),
                    'total_overflow_products': total_overflow_products,
                    'top_overflow': top_overflow[:10]  # Топ-10 самых переполненных
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting smart warehouse stats: {e}")
            return {
                'general': {'total_categories': 0, 'total_products': 0, 'total_stock': 0, 'total_unlimited': 0},
                'overflow': {'categories_with_overflow': 0, 'total_overflow_products': 0, 'top_overflow': []}
            }