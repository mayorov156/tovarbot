"""Клавиатуры для системы управления складом"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
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
    """Клавиатура после завершения действия на складе"""
    return warehouse_main_menu_kb()


def warehouse_main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню склада товаров - обновленная версия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📦 Все товары по категориям", callback_data="warehouse_all_products_compact")
    )
    builder.row(
        InlineKeyboardButton(text="📥 Добавить/Импортировать", callback_data="warehouse_add_menu")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрая выдача", callback_data="warehouse_quick_give")
    )
    builder.row(
        InlineKeyboardButton(text="📂 Создать категорию", callback_data="warehouse_create_category"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="warehouse_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_add_menu_kb() -> InlineKeyboardMarkup:
    """Меню способов добавления товаров"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="warehouse_add_product")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Массовое добавление", callback_data="warehouse_mass_add")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data="warehouse_quick_add")
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
    """Клавиатура после создания категории"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар в категорию", callback_data="warehouse_add_product")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Массово добавить товары", callback_data="warehouse_mass_add")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
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
    """Компактная клавиатура категорий с количеством товаров"""
    builder = InlineKeyboardBuilder()
    
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
        
        button_text = f"📂 {category['name']} ({stock_info} шт.)"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"warehouse_category_products_{category['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_all_products_compact")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_category_products_kb(products: List[Product], category_id: int, category_name: str, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура товаров в категории с управлением"""
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
        action_buttons = []
        if product.is_unlimited or product.stock_quantity > 0:
            action_buttons.append(
                InlineKeyboardButton(text="🎯 Выдать", callback_data=f"warehouse_give_single_{product.id}")
            )
        action_buttons.extend([
            InlineKeyboardButton(text="📝 Редактировать", callback_data=f"warehouse_edit_{product.id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"warehouse_delete_{product.id}")
        ])
        
        builder.row(*action_buttons)
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"warehouse_category_products_{category_id}_{page-1}")
        )
    
    if end < len(products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"warehouse_category_products_{category_id}_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"warehouse_category_products_{category_id}_0")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Все категории", callback_data="warehouse_all_products_compact")
    )
    
    return builder.as_markup()