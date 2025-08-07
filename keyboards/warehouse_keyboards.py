"""Клавиатуры для системы управления складом"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from database.models import Category, Product, ProductType


def product_type_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа товара"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="👤 Аккаунт (логин/пароль)",
            callback_data=f"warehouse_type_{ProductType.ACCOUNT.value}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔑 Ключ активации",
            callback_data=f"warehouse_type_{ProductType.KEY.value}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎫 Промокод",
            callback_data=f"warehouse_type_{ProductType.PROMO.value}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_cancel")
    )
    
    return builder.as_markup()


def warehouse_categories_select_kb(categories: List[Category]) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории для добавления товара"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📂 {category.name}",
                callback_data=f"warehouse_select_category_{category.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_cancel")
    )
    
    return builder.as_markup()


def warehouse_products_select_kb(products: List[Product]) -> InlineKeyboardMarkup:
    """Клавиатура выбора товара для выдачи"""
    builder = InlineKeyboardBuilder()
    
    for product in products:
        if product.stock_quantity > 0 or product.is_unlimited:
            stock_info = "∞" if product.is_unlimited else str(product.stock_quantity)
            builder.row(
                InlineKeyboardButton(
                    text=f"📦 {product.name} ({stock_info} шт.) - {product.price:.2f}₽",
                    callback_data=f"warehouse_select_product_{product.id}"
                )
            )
    
    if not any((p.stock_quantity > 0 or p.is_unlimited) for p in products):
        builder.row(
            InlineKeyboardButton(
                text="📭 Нет товаров в наличии",
                callback_data="warehouse_no_products"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_cancel")
    )
    
    return builder.as_markup()


def confirmation_kb(confirm_callback: str, cancel_callback: str = "warehouse_cancel") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_callback),
        InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)
    )
    
    return builder.as_markup()


def add_product_confirmation_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения добавления товара"""
    return confirmation_kb("warehouse_confirm_add_product")


def give_product_confirmation_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения выдачи товара"""
    return confirmation_kb("warehouse_confirm_give_product")


def cancel_kb() -> InlineKeyboardMarkup:
    """Простая клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_cancel")
    )
    
    return builder.as_markup()


def back_to_warehouse_kb() -> InlineKeyboardMarkup:
    """Клавиатура возврата к складу"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_action_complete_kb() -> InlineKeyboardMarkup:
    """Клавиатура после завершения действия на складе с быстрыми действиями"""
    builder = InlineKeyboardBuilder()
    
    # Быстрые действия для продолжения работы
    builder.row(
        InlineKeyboardButton(text="⚡ Выдать еще", callback_data="warehouse_quick_give"),
        InlineKeyboardButton(text="📦 Добавить товар", callback_data="warehouse_add_product")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Все товары", callback_data="warehouse_all_products_compact")
    )
    builder.row(
        InlineKeyboardButton(text="🏪 Главное меню склада", callback_data="warehouse_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_product_action_complete_kb(category_id: int, page: int = 0, action_type: str = "action") -> InlineKeyboardMarkup:
    """Улучшенная клавиатура после действий с товаром - возврат в категорию"""
    builder = InlineKeyboardBuilder()
    
    # Определяем текст в зависимости от типа действия
    action_buttons = {
        "delete": ("🗑 Удалить еще", f"warehouse_show_category_{category_id}"),
        "edit": ("📝 Редактировать еще", f"warehouse_show_category_{category_id}"),
        "give": ("🎯 Выдать еще", "warehouse_quick_give"),
        "add": ("➕ Добавить еще", f"warehouse_add_to_category_{category_id}")
    }
    
    # Первая строка - повторить действие + вернуться к категории
    action_text, action_callback = action_buttons.get(action_type, ("🔄 Повторить", f"warehouse_show_category_{category_id}"))
    builder.row(
        InlineKeyboardButton(text="📂 К категории", callback_data=f"warehouse_show_category_{category_id}_{page}"),
        InlineKeyboardButton(text=action_text, callback_data=action_callback)
    )
    
    # Вторая строка - быстрые действия с категорией
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}"),
        InlineKeyboardButton(text="🎯 Выдать товар", callback_data="warehouse_quick_give")
    )
    
    # Третья строка - навигация
    builder.row(
        InlineKeyboardButton(text="📊 Все категории", callback_data="warehouse_menu"),
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_main_menu_kb() -> InlineKeyboardMarkup:
    """Классическое главное меню склада с иерархической структурой"""
    builder = InlineKeyboardBuilder()
    
    # Основная навигация
    builder.row(
        InlineKeyboardButton(text="📦 Все товары", callback_data="warehouse_all_products")
    )
    
    # Управление остатками
    builder.row(
        InlineKeyboardButton(text="🟢 Товары с остатками", callback_data="warehouse_products_with_stock"),
        InlineKeyboardButton(text="🔴 Товары без остатков", callback_data="warehouse_show_out_of_stock")
    )
    
    # Быстрые действия управления
    builder.row(
        InlineKeyboardButton(text="📥 Добавить/Импорт", callback_data="warehouse_add_menu"),
        InlineKeyboardButton(text="🎯 Выдать/Быстро", callback_data="warehouse_give_menu")
    )
    
    # Управление структурой
    builder.row(
        InlineKeyboardButton(text="📂 Категории", callback_data="warehouse_categories_menu"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="warehouse_stats")
    )
    
    # Дополнительные возможности  
    builder.row(
        InlineKeyboardButton(text="📋 История выдач", callback_data="warehouse_history"),
        InlineKeyboardButton(text="⚙️ Настройки отображения", callback_data="warehouse_display_settings")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_categories_main_kb() -> InlineKeyboardMarkup:
    """Главный экран склада с категориями и быстрыми действиями"""
    builder = InlineKeyboardBuilder()
    
    # Этот экран будет динамически обновляться через обработчик
    # Здесь только базовые кнопки управления
    
    # Основные действия
    builder.row(
        InlineKeyboardButton(text="📥 Добавить/Импорт", callback_data="warehouse_add_menu"),
        InlineKeyboardButton(text="🎯 Выдать/Быстро", callback_data="warehouse_give_menu")
    )
    
    # Управление
    builder.row(
        InlineKeyboardButton(text="📂 Новая категория", callback_data="warehouse_create_category"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="warehouse_stats")
    )
    
    # Дополнительные возможности  
    builder.row(
        InlineKeyboardButton(text="📋 История выдач", callback_data="warehouse_history"),
        InlineKeyboardButton(text="🔧 Управление", callback_data="warehouse_management")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_main_categories_kb(category_stats: List[dict]) -> InlineKeyboardMarkup:
    """Главный экран склада - список категорий с товарами"""
    builder = InlineKeyboardBuilder()
    
    if not category_stats:
        # Если категорий нет
        builder.row(
            InlineKeyboardButton(text="📂 Создать первую категорию", callback_data="warehouse_create_category")
        )
    else:
        # Показываем категории
        for category in category_stats:
            # Формируем строку с информацией о категории
            stock_info = ""
            if category['unlimited_products'] > 0:
                stock_info += f"∞x{category['unlimited_products']}"
            if category['total_stock'] > 0:
                if stock_info:
                    stock_info += f" + {category['total_stock']}"
                else:
                    stock_info = str(category['total_stock'])
            
            if not stock_info:
                stock_info = "0" 
            
            # Иконка статуса категории
            if category['total_products'] == 0:
                icon = "📁"  # Пустая категория
            elif category['unlimited_products'] > 0 or category['total_stock'] > 0:
                icon = "📂"  # Категория с товарами
            else:
                icon = "🔴"  # Категория без остатков
            
            button_text = f"{icon} {category['name']} ({category['total_products']} товаров, {stock_info} шт.)"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"warehouse_show_category_{category['id']}"
                )
            )
    
    # Управление остатками
    builder.row(
        InlineKeyboardButton(text="🟢 Товары с остатками", callback_data="warehouse_products_with_stock"),
        InlineKeyboardButton(text="🔴 Товары без остатков", callback_data="warehouse_show_out_of_stock")
    )
    
    # Быстрые действия внизу
    builder.row(
        InlineKeyboardButton(text="📥 Добавить/Импорт", callback_data="warehouse_add_menu"),
        InlineKeyboardButton(text="🎯 Выдать/Быстро", callback_data="warehouse_give_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="📂 Новая категория", callback_data="warehouse_create_category"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="warehouse_stats")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_menu"),
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_add_menu_kb() -> InlineKeyboardMarkup:
    """Улучшенное меню способов добавления товаров"""
    builder = InlineKeyboardBuilder()
    
    # Основные способы добавления
    builder.row(
        InlineKeyboardButton(text="➕ Один товар", callback_data="warehouse_add_product"),
        InlineKeyboardButton(text="📦 Массово", callback_data="warehouse_mass_add")
    )
    
    # Быстрые способы
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data="warehouse_quick_add")
    )
    
    # Дополнительные функции
    builder.row(
        InlineKeyboardButton(text="📄 Импорт из файла", callback_data="warehouse_import_file"),
        InlineKeyboardButton(text="🔄 Дублировать товар", callback_data="warehouse_duplicate_product")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_give_menu_kb() -> InlineKeyboardMarkup:
    """Объединенное меню выдачи товаров"""
    builder = InlineKeyboardBuilder()
    
    # Основные способы выдачи
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрая выдача", callback_data="warehouse_quick_give"),
        InlineKeyboardButton(text="🎯 Выбрать товар", callback_data="warehouse_give_product")  
    )
    
    # Дополнительные опции
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск товара", callback_data="warehouse_search_product"),
        InlineKeyboardButton(text="👥 Найти пользователя", callback_data="warehouse_find_user")
    )
    
    # Массовые операции
    builder.row(
        InlineKeyboardButton(text="📦 Массовая выдача", callback_data="warehouse_mass_give")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_quick_master_kb() -> InlineKeyboardMarkup:
    """Клавиатура быстрого мастера - объединенный интерфейс"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрая выдача", callback_data="warehouse_quick_give")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def category_created_kb(category_id: int) -> InlineKeyboardMarkup:
    """Улучшенная клавиатура после создания категории с быстрыми действиями"""
    builder = InlineKeyboardBuilder()
    
    # Главные действия для новой категории
    builder.row(
        InlineKeyboardButton(text="🎯 Добавить товар сейчас", callback_data=f"warehouse_add_to_category_{category_id}"),
        InlineKeyboardButton(text="📦 Массово заполнить", callback_data=f"warehouse_mass_add_to_category_{category_id}")
    )
    
    # Быстрые действия
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data=f"warehouse_quick_add_to_category_{category_id}")
    )
    
    # Навигация
    builder.row(
        InlineKeyboardButton(text="📂 Создать еще категорию", callback_data="warehouse_create_category"),
        InlineKeyboardButton(text="📊 Все товары", callback_data="warehouse_all_products_compact")
    )
    builder.row(
        InlineKeyboardButton(text="🏪 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_all_products_kb(products: List[Product], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура всех товаров с управлением"""
    builder = InlineKeyboardBuilder()
    
    # Пагинация
    start = page * per_page
    end = start + per_page
    page_products = products[start:end]
    
    for product in page_products:
        # Показываем остатки товара
        if product.is_unlimited:
            stock_info = "∞"
        else:
            stock_info = f"{product.stock_quantity}"
            
        status = "🟢" if (product.is_unlimited or product.stock_quantity > 0) else "🔴"
        
        # Название товара
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {product.name} ({stock_info}) - {product.price:.2f}₽",
                callback_data=f"warehouse_product_info_{product.id}"
            )
        )
        
        # Кнопки управления товаром
        builder.row(
            InlineKeyboardButton(text="📝 Редактировать", callback_data=f"warehouse_edit_{product.id}"),
            InlineKeyboardButton(text="🎯 Выдать", callback_data=f"warehouse_give_single_{product.id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"warehouse_delete_{product.id}")
        )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_all_products_page_{page-1}")
        )
    
    if end < len(products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"warehouse_all_products_page_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_all_products")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def create_category_confirmation_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения создания категории"""
    return confirmation_kb("warehouse_confirm_create_category")


def no_categories_warning_kb() -> InlineKeyboardMarkup:
    """Клавиатура предупреждения об отсутствии категорий"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📂 Создать категорию", callback_data="warehouse_create_category")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def mass_add_confirmation_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения массового добавления"""
    return confirmation_kb("warehouse_confirm_mass_add")


def edit_product_fields_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования товара"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏷 Название", callback_data="edit_field_name")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Тип товара", callback_data="edit_field_type")
    )
    builder.row(
        InlineKeyboardButton(text="⏱ Длительность", callback_data="edit_field_duration")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Цена", callback_data="edit_field_price")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Содержимое", callback_data="edit_field_content")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_cancel")
    )
    
    return builder.as_markup()


def edit_product_type_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа товара при редактировании"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="👤 Аккаунт (логин/пароль)",
            callback_data=f"edit_type_{ProductType.ACCOUNT.value}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔑 Ключ активации",
            callback_data=f"edit_type_{ProductType.KEY.value}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎫 Промокод",
            callback_data=f"edit_type_{ProductType.PROMO.value}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_cancel")
    )
    
    return builder.as_markup()


def edit_product_confirmation_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения редактирования товара"""
    return confirmation_kb("warehouse_confirm_edit_product")


def warehouse_categories_compact_kb(category_stats: List[dict]) -> InlineKeyboardMarkup:
    """Иерархическая клавиатура всех товаров по категориям"""
    builder = InlineKeyboardBuilder()
    
    if not category_stats:
        # Если категорий нет
        builder.row(
            InlineKeyboardButton(text="📂 Создать первую категорию", callback_data="warehouse_create_category")
        )
        builder.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="warehouse_menu")
        )
        return builder.as_markup()
    
    for category in category_stats:
        # Формируем строку с информацией о категории
        stock_info = ""
        if category['unlimited_products'] > 0:
            stock_info += f"∞x{category['unlimited_products']}"
        if category['total_stock'] > 0:
            if stock_info:
                stock_info += f" + {category['total_stock']}"
            else:
                stock_info = str(category['total_stock'])
        
        if not stock_info:
            stock_info = "0"
        
        # Иконка статуса категории
        if category['total_products'] == 0:
            icon = "📁"  # Пустая категория
        elif category['unlimited_products'] > 0 or category['total_stock'] > 0:
            icon = "📂"  # Категория с товарами в наличии
        else:
            icon = "🔴"  # Категория без остатков
        
        button_text = f"{icon} {category['name']} ({category['total_products']} товаров, {stock_info} шт.)"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_show_category_{category['id']}"
            )
        )
    
    # Управление остатками
    builder.row(
        InlineKeyboardButton(text="🟢 Товары с остатками", callback_data="warehouse_products_with_stock"),
        InlineKeyboardButton(text="🔴 Товары без остатков", callback_data="warehouse_show_out_of_stock")
    )
    
    # Быстрые действия
    builder.row(
        InlineKeyboardButton(text="📂 Новая категория", callback_data="warehouse_create_category"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_all_products")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_display_settings_kb() -> InlineKeyboardMarkup:
    """Клавиатура настроек отображения товаров"""
    builder = InlineKeyboardBuilder()
    
    # Настройки отображения
    builder.row(
        InlineKeyboardButton(text="📋 Плоское отображение", callback_data="warehouse_set_display_flat"),
        InlineKeyboardButton(text="🗂 Иерархическое", callback_data="warehouse_set_display_hierarchy")
    )
    
    # Настройки пагинации
    builder.row(
        InlineKeyboardButton(text="📄 5 на странице", callback_data="warehouse_set_per_page_5"),
        InlineKeyboardButton(text="📄 10 на странице", callback_data="warehouse_set_per_page_10")
    )
    
    # Настройки сортировки
    builder.row(
        InlineKeyboardButton(text="🔤 По алфавиту", callback_data="warehouse_set_sort_name"),
        InlineKeyboardButton(text="📊 По остатку", callback_data="warehouse_set_sort_stock")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_category_products_kb(products: List[Product], category_id: int, category_name: str, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Компактная клавиатура товаров в категории"""
    builder = InlineKeyboardBuilder()
    
    # Пагинация
    start = page * per_page
    end = start + per_page
    page_products = products[start:end]
    
    # Отображаем товары компактно - только по 1 кнопке на товар
    for product in page_products:
        # Показываем остатки товара
        if product.is_unlimited:
            stock_info = "∞"
        else:
            stock_info = f"{product.stock_quantity}"
            
        # Статус иконка
        if product.is_unlimited or product.stock_quantity > 0:
            status = "🟢"
        elif product.stock_quantity == 0:
            status = "🔴"
        else:
            status = "🟡"
        
        # Компактное отображение: статус, название, остаток, цена
        button_text = f"{status} {product.name[:25]}{'...' if len(product.name) > 25 else ''} • {stock_info} шт • {product.price:.0f}₽"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_product_detail_{product.id}_{category_id}_{page}"
            )
        )
    
    # Убираем массовые операции для упрощения интерфейса
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_show_category_{category_id}_{page-1}")
        )
    
    if end < len(products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"warehouse_show_category_{category_id}_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Убираем кнопки управления и массового удаления для упрощения интерфейса
    
    # Кнопки навигации - только основные
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="warehouse_all_products"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"warehouse_show_category_{category_id}_0")
    )
    
    return builder.as_markup()


def warehouse_product_detail_kb(product_id: int, category_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра товара с действиями"""
    builder = InlineKeyboardBuilder()
    
    # Основные действия с товаром
    builder.row(
        InlineKeyboardButton(text="🎯 Выдать", callback_data=f"warehouse_give_single_{product_id}"),
        InlineKeyboardButton(text="📝 Редактировать", callback_data=f"warehouse_edit_{product_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Дублировать", callback_data=f"warehouse_duplicate_{product_id}"),
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"warehouse_delete_{product_id}")
    )
    
    # Быстрые действия категории
    builder.row(
        InlineKeyboardButton(text="➕ Добавить похожий", callback_data=f"warehouse_add_to_category_{category_id}"),
    )
    
    # Навигация с иерархической структурой - возврат к единому управлению
    builder.row(
        InlineKeyboardButton(text="🎛 Управление категорией", callback_data=f"warehouse_category_management_{category_id}_{page}"),
        InlineKeyboardButton(text="📂 Все товары", callback_data="warehouse_all_products")
    )
    
    return builder.as_markup()


def warehouse_error_recovery_kb(category_id: Optional[int] = None, action_type: str = "general") -> InlineKeyboardMarkup:
    """Клавиатура восстановления после ошибок с контекстными действиями"""
    builder = InlineKeyboardBuilder()
    
    if category_id:
        # Если знаем категорию, предлагаем контекстные действия
        if action_type == "mass_add":
            builder.row(
                InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data=f"warehouse_mass_add_to_category_{category_id}"),
                InlineKeyboardButton(text="📂 К категории", callback_data=f"warehouse_show_category_{category_id}_0")
            )
            builder.row(
                InlineKeyboardButton(text="➕ Добавить один товар", callback_data=f"warehouse_add_to_category_{category_id}"),
                InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data=f"warehouse_quick_add_to_category_{category_id}")
            )
        elif action_type == "add_product":
            builder.row(
                InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data=f"warehouse_add_to_category_{category_id}"),
                InlineKeyboardButton(text="📂 К категории", callback_data=f"warehouse_show_category_{category_id}_0")
            )
            builder.row(
                InlineKeyboardButton(text="📦 Массово добавить", callback_data=f"warehouse_mass_add_to_category_{category_id}"),
                InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data=f"warehouse_quick_add_to_category_{category_id}")
            )
        else:
            # Общие действия для категории
            builder.row(
                InlineKeyboardButton(text="📂 К категории", callback_data=f"warehouse_show_category_{category_id}_0"),
                InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}")
            )
            builder.row(
                InlineKeyboardButton(text="📦 Массово добавить", callback_data=f"warehouse_mass_add_to_category_{category_id}"),
                InlineKeyboardButton(text="🎯 Выдать товар", callback_data="warehouse_quick_give")
            )
    else:
        # Если категория неизвестна, общие действия
        builder.row(
            InlineKeyboardButton(text="📦 Все товары", callback_data="warehouse_all_products"),
            InlineKeyboardButton(text="📂 Создать категорию", callback_data="warehouse_create_category")
        )
        builder.row(
            InlineKeyboardButton(text="➕ Добавить товар", callback_data="warehouse_add_product"),
            InlineKeyboardButton(text="🎯 Выдать товар", callback_data="warehouse_quick_give")
        )
    
    # Общая навигация
    builder.row(
        InlineKeyboardButton(text="🏪 Главное меню склада", callback_data="warehouse_menu"),
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_categories_management_kb(categories: List[Category], category_products_count: dict = None) -> InlineKeyboardMarkup:
    """Меню управления категориями"""
    builder = InlineKeyboardBuilder()
    
    if not categories:
        # Если категорий нет
        builder.row(
            InlineKeyboardButton(text="📂 Создать первую категорию", callback_data="warehouse_create_category")
        )
    else:
        # Показываем существующие категории
        for category in categories:
            # Получаем количество товаров из переданного словаря
            if category_products_count and category.id in category_products_count:
                product_count = category_products_count[category.id]
                if product_count == 1:
                    category_info = f"📂 {category.name} ({product_count} товар)"
                elif 2 <= product_count <= 4:
                    category_info = f"📂 {category.name} ({product_count} товара)"
                else:
                    category_info = f"📂 {category.name} ({product_count} товаров)"
            else:
                category_info = f"📂 {category.name}"
            
            builder.row(
                InlineKeyboardButton(
                    text=category_info,
                    callback_data=f"warehouse_manage_category_{category.id}"
                )
            )
        
        # Действия с категориями
        builder.row(
            InlineKeyboardButton(text="📂 Новая категория", callback_data="warehouse_create_category"),
            InlineKeyboardButton(text="🔄 Обновить список", callback_data="warehouse_categories_menu")
        )
        
        if len(categories) > 1:
            builder.row(
                InlineKeyboardButton(text="📊 Статистика категорий", callback_data="warehouse_categories_stats"),
                InlineKeyboardButton(text="🗑 Массовые операции", callback_data="warehouse_categories_bulk")
            )
    
    # Навигация
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_category_management_kb(category_id: int) -> InlineKeyboardMarkup:
    """Меню управления конкретной категорией"""
    builder = InlineKeyboardBuilder()
    
    # Основные действия с категорией
    builder.row(
        InlineKeyboardButton(text="👁 Просмотр товаров", callback_data=f"warehouse_show_category_{category_id}_0"),
        InlineKeyboardButton(text="📝 Редактировать", callback_data=f"warehouse_edit_category_{category_id}")
    )
    
    # Действия с товарами категории
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}"),
        InlineKeyboardButton(text="📦 Массово добавить", callback_data=f"warehouse_mass_add_to_category_{category_id}")
    )
    
    # Управление
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data=f"warehouse_category_stats_{category_id}"),
        InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"warehouse_delete_category_{category_id}")
    )
    
    # Навигация
    builder.row(
        InlineKeyboardButton(text="📂 К категориям", callback_data="warehouse_categories_menu"),
        InlineKeyboardButton(text="🏪 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_category_unified_management_kb(
    products: List[Product], 
    category_id: int, 
    category_name: str, 
    page: int = 0, 
    per_page: int = 10
) -> InlineKeyboardMarkup:
    """Единое меню управления категорией - включает товары, статистику и все действия"""
    builder = InlineKeyboardBuilder()
    
    # Пагинация товаров
    start = page * per_page
    end = start + per_page
    page_products = products[start:end]
    
    if products:
        # Показываем товары компактно с действиями
        for product in page_products:
            # Определяем статус товара
            if product.is_unlimited:
                stock_info = "∞"
                status = "🟢"
            else:
                stock_info = f"{product.stock_quantity}"
                status = "🟢" if product.stock_quantity > 0 else "🔴"
            
            # Компактная информация о товаре
            product_name = product.name[:20] + "..." if len(product.name) > 20 else product.name
            button_text = f"{status} {product_name} • {stock_info} • {product.price:.0f}₽"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"warehouse_product_detail_{product.id}_{category_id}_{page}"
                )
            )
        
        # Кнопки пагинации товаров
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_category_management_{category_id}_{page-1}")
            )
        if end < len(products):
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"warehouse_category_management_{category_id}_{page+1}")
            )
        
        if nav_buttons:
            builder.row(*nav_buttons)
            
        # Разделитель
        builder.row(
            InlineKeyboardButton(text="━━━━━ ДЕЙСТВИЯ С ТОВАРАМИ ━━━━━", callback_data="noop")
        )
    
    # Действия с товарами в категории
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}"),
        InlineKeyboardButton(text="📦 Массово добавить", callback_data=f"warehouse_mass_add_to_category_{category_id}")
    )
    
    if products:  # Если есть товары
        builder.row(
            InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data=f"warehouse_quick_add_to_category_{category_id}"),
            InlineKeyboardButton(text="🎯 Выдать товар", callback_data="warehouse_quick_give")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Массово удалить", callback_data=f"warehouse_mass_delete_category_{category_id}"),
            InlineKeyboardButton(text="📊 Статистика товаров", callback_data=f"warehouse_category_products_stats_{category_id}")
        )
    
    # Разделитель  
    builder.row(
        InlineKeyboardButton(text="━━━━━ УПРАВЛЕНИЕ КАТЕГОРИЕЙ ━━━━━", callback_data="noop")
    )
    
    # Действия с самой категорией
    builder.row(
        InlineKeyboardButton(text="📝 Редактировать категорию", callback_data=f"warehouse_edit_category_{category_id}"),
        InlineKeyboardButton(text="📊 Статистика категории", callback_data=f"warehouse_category_stats_{category_id}")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"warehouse_category_management_{category_id}_{page}"),
        InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"warehouse_delete_category_{category_id}")
    )
    
    # Навигация
    builder.row(
        InlineKeyboardButton(text="📂 К категориям", callback_data="warehouse_categories_menu"),
        InlineKeyboardButton(text="🏪 Главное меню", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_category_action_complete_kb(category_id: int, page: int = 0, action_type: str = "action") -> InlineKeyboardMarkup:
    """Клавиатура возврата после действий с товарами в категории - возврат к единому управлению"""
    builder = InlineKeyboardBuilder()
    
    # Действие зависит от типа операции
    if action_type == "add":
        builder.row(
            InlineKeyboardButton(text="➕ Добавить еще", callback_data=f"warehouse_add_to_category_{category_id}"),
            InlineKeyboardButton(text="📦 Массово добавить", callback_data=f"warehouse_mass_add_to_category_{category_id}")
        )
    elif action_type == "edit":
        builder.row(
            InlineKeyboardButton(text="📝 Редактировать еще", callback_data=f"warehouse_add_to_category_{category_id}"),
            InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}")
        )
    elif action_type == "delete":
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить еще", callback_data=f"warehouse_mass_delete_category_{category_id}"),
            InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}")
        )
    elif action_type == "give":
        builder.row(
            InlineKeyboardButton(text="🎯 Выдать еще", callback_data="warehouse_quick_give"),
            InlineKeyboardButton(text="📊 Статистика", callback_data=f"warehouse_category_stats_{category_id}")
        )
    else:
        # Общие действия
        builder.row(
            InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"warehouse_add_to_category_{category_id}"),
            InlineKeyboardButton(text="📦 Массово добавить", callback_data=f"warehouse_mass_add_to_category_{category_id}")
        )
    
    # Главные кнопки навигации - всегда возврат к единому управлению
    builder.row(
        InlineKeyboardButton(text="🎛 Управление категорией", callback_data=f"warehouse_category_management_{category_id}_{page}"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"warehouse_category_management_{category_id}_{page}")
    )
    
    # Дополнительная навигация
    builder.row(
        InlineKeyboardButton(text="📂 К категориям", callback_data="warehouse_categories_menu"),
        InlineKeyboardButton(text="🏪 Главное меню", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_products_with_stock_kb(products: List[Product], page: int = 0, per_page: int = 10, category_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура товаров с остатками и пагинацией"""
    builder = InlineKeyboardBuilder()
    
    # Фильтруем товары с остатками
    available_products = [p for p in products if p.is_unlimited or p.stock_quantity > 0]
    out_of_stock_products = [p for p in products if not p.is_unlimited and p.stock_quantity <= 0]
    
    # Пагинация для доступных товаров
    start = page * per_page
    end = start + per_page
    page_products = available_products[start:end]
    
    # Показываем доступные товары
    for product in page_products:
        if product.is_unlimited:
            stock_info = "∞"
            status = "🟢"
        else:
            stock_info = f"{product.stock_quantity}"
            status = "🟢"
        
        button_text = f"{status} {product.name} • {stock_info} шт • {product.price:.0f}₽"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_select_product_{product.id}"
            )
        )
    
    # Показываем товары без остатков (если есть)
    if out_of_stock_products and page == 0:  # Только на первой странице
        builder.row(
            InlineKeyboardButton(text="━━━━━ ЗАКОНЧИЛСЯ ━━━━━", callback_data="noop")
        )
        
        for product in out_of_stock_products[:3]:  # Показываем только первые 3
            button_text = f"🔴 {product.name} • ЗАКОНЧИЛСЯ • {product.price:.0f}₽"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"warehouse_product_out_of_stock_{product.id}"
                )
            )
        
        if len(out_of_stock_products) > 3:
            builder.row(
                InlineKeyboardButton(
                    text=f"🔴 И еще {len(out_of_stock_products) - 3} товаров закончилось",
                    callback_data="warehouse_show_out_of_stock"
                )
            )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_products_stock_page_{page-1}")
        )
    
    # Показываем информацию о страницах
    total_pages = (len(available_products) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
        )
    
    if end < len(available_products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"warehouse_products_stock_page_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Информация о товарах
    builder.row(
        InlineKeyboardButton(
            text=f"📦 Доступно: {len(available_products)} | 🔴 Закончилось: {len(out_of_stock_products)}",
            callback_data="noop"
        )
    )
    
    # Упрощенные кнопки навигации
    if category_id:
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"warehouse_show_category_{category_id}"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_products_with_stock")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="warehouse_menu"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_products_with_stock")
        )
    
    return builder.as_markup()


def warehouse_category_products_with_stock_kb(
    products: List[Product], 
    category_id: int, 
    category_name: str, 
    page: int = 0, 
    per_page: int = 10
) -> InlineKeyboardMarkup:
    """Клавиатура товаров категории с остатками"""
    builder = InlineKeyboardBuilder()
    
    # Фильтруем товары
    available_products = [p for p in products if p.is_unlimited or p.stock_quantity > 0]
    out_of_stock_products = [p for p in products if not p.is_unlimited and p.stock_quantity <= 0]
    
    # Пагинация для доступных товаров
    start = page * per_page
    end = start + per_page
    page_products = available_products[start:end]
    
    # Заголовок категории
    builder.row(
        InlineKeyboardButton(
            text=f"📂 {category_name} • {len(available_products)} доступно • {len(out_of_stock_products)} закончилось",
            callback_data="noop"
        )
    )
    
    # Показываем доступные товары
    for product in page_products:
        if product.is_unlimited:
            stock_info = "∞"
            status = "🟢"
        else:
            stock_info = f"{product.stock_quantity}"
            status = "🟢"
        
        # Компактное отображение
        product_name = product.name[:25] + "..." if len(product.name) > 25 else product.name
        button_text = f"{status} {product_name} • {stock_info} • {product.price:.0f}₽"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_product_detail_{product.id}_{category_id}_{page}"
            )
        )
    
    # Показываем товары без остатков (если есть и на первой странице)
    if out_of_stock_products and page == 0:
        builder.row(
            InlineKeyboardButton(text="━━━━━ ЗАКОНЧИЛСЯ ━━━━━", callback_data="noop")
        )
        
        for product in out_of_stock_products[:2]:  # Показываем только первые 2
            product_name = product.name[:20] + "..." if len(product.name) > 20 else product.name
            button_text = f"🔴 {product_name} • ЗАКОНЧИЛСЯ • {product.price:.0f}₽"
            
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"warehouse_product_out_of_stock_{product.id}"
                )
            )
        
        if len(out_of_stock_products) > 2:
            builder.row(
                InlineKeyboardButton(
                    text=f"🔴 И еще {len(out_of_stock_products) - 2} товаров закончилось",
                    callback_data=f"warehouse_show_category_out_of_stock_{category_id}"
                )
            )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_category_stock_page_{category_id}_{page-1}")
        )
    
    # Показываем информацию о страницах
    total_pages = (len(available_products) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
        )
    
    if end < len(available_products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"warehouse_category_stock_page_{category_id}_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Упрощенные кнопки навигации
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="warehouse_categories_menu"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"warehouse_category_products_with_stock_{category_id}_0")
    )
    
    return builder.as_markup()


def warehouse_out_of_stock_products_kb(products: List[Product], page: int = 0, per_page: int = 10, category_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура товаров без остатков"""
    builder = InlineKeyboardBuilder()
    
    # Фильтруем только товары без остатков
    out_of_stock_products = [p for p in products if not p.is_unlimited and p.stock_quantity <= 0]
    
    # Пагинация
    start = page * per_page
    end = start + per_page
    page_products = out_of_stock_products[start:end]
    
    builder.row(
        InlineKeyboardButton(
            text=f"🔴 Товары без остатков ({len(out_of_stock_products)} шт.)",
            callback_data="noop"
        )
    )
    
    # Показываем товары без остатков
    for product in page_products:
        product_name = product.name[:30] + "..." if len(product.name) > 30 else product.name
        button_text = f"🔴 {product_name} • {product.price:.0f}₽"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_product_out_of_stock_{product.id}"
            )
        )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_out_of_stock_page_{page-1}")
        )
    
    # Показываем информацию о страницах
    total_pages = (len(out_of_stock_products) + per_page - 1) // per_page
    if total_pages > 1:
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
        )
    
    if end < len(out_of_stock_products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"warehouse_out_of_stock_page_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="📦 Добавить остатки", callback_data="warehouse_add_stock"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_show_out_of_stock")
    )
    
    if category_id:
        builder.row(
            InlineKeyboardButton(text="📂 К категории", callback_data=f"warehouse_show_category_{category_id}"),
            InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
        )
    
    return builder.as_markup()


def warehouse_stock_summary_kb(categories: List[dict]) -> InlineKeyboardMarkup:
    """Клавиатура сводки по остаткам по категориям"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Сводка по остаткам",
            callback_data="noop"
        )
    )
    
    # Показываем категории с информацией об остатках
    for category in categories:
        available_count = category.get('available_products', 0)
        out_of_stock_count = category.get('out_of_stock_products', 0)
        total_stock = category.get('total_stock', 0)
        
        # Определяем статус категории
        if available_count > 0:
            status = "🟢"
        elif out_of_stock_count > 0:
            status = "🔴"
        else:
            status = "⚪"
        
        button_text = f"{status} {category['name']} • {available_count} доступно • {out_of_stock_count} закончилось"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_category_stock_summary_{category['id']}"
            )
        )
    
    # Общая статистика
    total_available = sum(cat.get('available_products', 0) for cat in categories)
    total_out_of_stock = sum(cat.get('out_of_stock_products', 0) for cat in categories)
    
    builder.row(
        InlineKeyboardButton(
            text=f"📦 Всего доступно: {total_available} | 🔴 Закончилось: {total_out_of_stock}",
            callback_data="noop"
        )
    )
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="📦 Добавить остатки", callback_data="warehouse_add_stock"),
        InlineKeyboardButton(text="🔴 Показать закончившиеся", callback_data="warehouse_show_out_of_stock")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_stock_summary"),
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_quick_stock_select_kb(products: List[Product], action: str = "give") -> InlineKeyboardMarkup:
    """Быстрая клавиатура выбора товаров с остатками для выдачи"""
    builder = InlineKeyboardBuilder()
    
    # Фильтруем только товары с остатками
    available_products = [p for p in products if p.is_unlimited or p.stock_quantity > 0]
    
    builder.row(
        InlineKeyboardButton(
            text=f"🎯 Выберите товар для выдачи ({len(available_products)} доступно)",
            callback_data="noop"
        )
    )
    
    # Показываем товары с остатками
    for product in available_products[:10]:  # Ограничиваем 10 товарами
        if product.is_unlimited:
            stock_info = "∞"
        else:
            stock_info = f"{product.stock_quantity}"
        
        product_name = product.name[:25] + "..." if len(product.name) > 25 else product.name
        button_text = f"🟢 {product_name} • {stock_info} • {product.price:.0f}₽"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_quick_{action}_{product.id}"
            )
        )
    
    if len(available_products) > 10:
        builder.row(
            InlineKeyboardButton(
                text=f"📄 Показать еще {len(available_products) - 10} товаров",
                callback_data="warehouse_show_more_products"
            )
        )
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск товара", callback_data="warehouse_search_product"),
        InlineKeyboardButton(text="📂 По категориям", callback_data="warehouse_categories_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Отмена", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_stock_management_kb() -> InlineKeyboardMarkup:
    """Клавиатура управления остатками"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Сводка по остаткам", callback_data="warehouse_stock_summary")
    )
    
    builder.row(
        InlineKeyboardButton(text="🟢 Товары с остатками", callback_data="warehouse_products_with_stock"),
        InlineKeyboardButton(text="🔴 Товары без остатков", callback_data="warehouse_show_out_of_stock")
    )
    
    builder.row(
        InlineKeyboardButton(text="📦 Добавить остатки", callback_data="warehouse_add_stock"),
        InlineKeyboardButton(text="📋 Импорт остатков", callback_data="warehouse_import_stock")
    )
    
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки уведомлений", callback_data="warehouse_stock_notifications"),
        InlineKeyboardButton(text="📈 Статистика продаж", callback_data="warehouse_sales_stats")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()