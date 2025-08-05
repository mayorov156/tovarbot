from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional
from database.models import Category, Product, Order
from config import settings


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"),
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart"),
        InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{settings.SUPPORT_USERNAME}")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")
    )
    
    return builder.as_markup()


def categories_kb(categories: List[Category]) -> InlineKeyboardMarkup:
    """Клавиатура категорий"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📂 {category.name}",
                callback_data=f"category_{category.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def products_kb(products: List[Product], category_id: int, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура товаров с пагинацией"""
    builder = InlineKeyboardBuilder()
    
    # Пагинация
    start = page * per_page
    end = start + per_page
    page_products = products[start:end]
    
    for product in page_products:
        # Показываем доступность товара
        availability = "✅" if (product.is_unlimited or product.stock_quantity > 0) else "❌"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{availability} {product.name} - {product.price:.2f}₽",
                callback_data=f"product_{product.id}"
            )
        )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"products_{category_id}_{page-1}")
        )
    
    if end < len(products):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"products_{category_id}_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔙 К категориям", callback_data="catalog")
    )
    
    return builder.as_markup()


def product_detail_kb(product: Product, user_can_buy: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра товара"""
    builder = InlineKeyboardBuilder()
    
    if user_can_buy and (product.is_unlimited or product.stock_quantity > 0):
        builder.row(
            InlineKeyboardButton(
                text="🛒 Купить",
                callback_data=f"buy_{product.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"category_{product.category_id}")
    )
    
    return builder.as_markup()


def order_confirmation_kb(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заказа"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_order_{order_id}")
    )
    
    return builder.as_markup()


def user_orders_kb(orders: List[Order], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура заказов пользователя"""
    builder = InlineKeyboardBuilder()
    
    # Пагинация
    start = page * per_page
    end = start + per_page
    page_orders = orders[start:end]
    
    for order in page_orders:
        status_icon = "✅" if order.status == "delivered" else "🕐"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} Заказ #{order.id} - {order.total_price:.2f}₽",
                callback_data=f"order_details_{order.id}"
            )
        )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"cart_{page-1}")
        )
    
    if end < len(orders):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"cart_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Упрощенное админ меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🏪 Склад товаров", callback_data="warehouse_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def admin_orders_kb(orders: List[Order], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура заказов для админа"""
    builder = InlineKeyboardBuilder()
    
    # Пагинация
    start = page * per_page
    end = start + per_page
    page_orders = orders[start:end]
    
    for order in page_orders:
        status_icons = {
            "pending": "🕐",
            "paid": "💳",
            "delivered": "✅",
            "cancelled": "❌"
        }
        
        icon = status_icons.get(order.status, "❓")
        
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} #{order.id} - {order.product.name} - {order.total_price:.2f}₽",
                callback_data=f"admin_order_{order.id}"
            )
        )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"admin_orders_{page-1}")
        )
    
    if end < len(orders):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"admin_orders_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def order_management_kb(order: Order) -> InlineKeyboardMarkup:
    """Клавиатура управления заказом для админа"""
    builder = InlineKeyboardBuilder()
    
    if order.status in ["pending", "paid"]:
        builder.row(
            InlineKeyboardButton(
                text="✅ Выдать заказ",
                callback_data=f"deliver_order_{order.id}"
            )
        )
    
    if order.status != "cancelled":
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить заказ",
                callback_data=f"admin_cancel_order_{order.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 К заказам", callback_data="admin_orders")
    )
    
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💰 Зарабатывать", url=settings.EARNING_CHANNEL)
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def referrals_kb() -> InlineKeyboardMarkup:
    """Клавиатура рефералов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw_funds")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()


def back_button(callback_data: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Простая кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)
    )
    return builder.as_markup()


def confirm_cancel_kb(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel_action")
    )
    
    return builder.as_markup()


def warehouse_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню склада товаров - обновленная компактная версия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📦 Все товары", callback_data="warehouse_all_products")
    )
    builder.row(
        InlineKeyboardButton(text="📥 Добавить/Импортировать", callback_data="warehouse_add_menu")
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Быстрый мастер", callback_data="warehouse_quick_master")
    )
    builder.row(
        InlineKeyboardButton(text="📂 Создать категорию", callback_data="warehouse_create_category"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="warehouse_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def warehouse_products_kb(products: List[Product], page: int = 0, per_page: int = 5, category_filter: str = None) -> InlineKeyboardMarkup:
    """Клавиатура товаров на складе с остатками"""
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
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {product.name} ({stock_info}) - {product.price:.2f}₽",
                callback_data=f"warehouse_product_{product.id}"
            )
        )
    
    # Кнопки пагинации
    nav_buttons = []
    
    if page > 0:
        callback_prefix = f"warehouse_products_{category_filter or 'all'}"
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}_{page-1}")
        )
    
    if end < len(products):
        callback_prefix = f"warehouse_products_{category_filter or 'all'}"
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки фильтрации
    if not category_filter:
        builder.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="warehouse_all_products")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Склад", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def warehouse_product_actions_kb(product: Product) -> InlineKeyboardMarkup:
    """Клавиатура действий с товаром на складе"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📝 Редактировать", callback_data=f"warehouse_edit_{product.id}"),
        InlineKeyboardButton(text="🎯 Выдать", callback_data=f"warehouse_give_{product.id}")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Добавить остаток", callback_data=f"warehouse_add_stock_{product.id}"),
        InlineKeyboardButton(text="📉 Списать остаток", callback_data=f"warehouse_remove_stock_{product.id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Удалить товар", callback_data=f"warehouse_delete_{product.id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К товарам", callback_data="warehouse_all_products")
    )
    
    return builder.as_markup()


def warehouse_categories_kb(categories: List[Category]) -> InlineKeyboardMarkup:
    """Клавиатура категорий для склада"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📂 {category.name}",
                callback_data=f"warehouse_category_{category.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Склад", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()


def admin_users_menu_kb() -> InlineKeyboardMarkup:
    """Меню управления пользователями"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏆 Топ покупателей", callback_data="admin_users_top_buyers")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Активные пользователи", callback_data="admin_users_active")
    )
    builder.row(
        InlineKeyboardButton(text="🆕 Новые пользователи", callback_data="admin_users_recent")
    )
    builder.row(
        InlineKeyboardButton(text="💰 С балансом", callback_data="admin_users_balance")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_users_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def admin_users_back_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата к меню пользователей"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔙 К пользователям", callback_data="admin_users")
    )
    
    return builder.as_markup()


def admin_settings_menu_kb() -> InlineKeyboardMarkup:
    """Меню настроек системы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💰 Реферальная система", callback_data="admin_settings_category_referral")
    )
    builder.row(
        InlineKeyboardButton(text="📞 Контакты", callback_data="admin_settings_category_contacts")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Сообщения", callback_data="admin_settings_category_messages")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Финансы", callback_data="admin_settings_category_financial")
    )
    # builder.row(
    #     InlineKeyboardButton(text="📋 Все настройки", callback_data="admin_settings_all")
    # )
    builder.row(
        InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
    )
    
    return builder.as_markup()


def admin_settings_category_kb(settings: List, category: str) -> InlineKeyboardMarkup:
    """Клавиатура настроек в категории"""
    builder = InlineKeyboardBuilder()
    
    for setting in settings:
        # Показываем краткое значение настройки
        value_preview = str(setting.value)
        if len(value_preview) > 20:
            value_preview = value_preview[:17] + "..."
        
        button_text = f"⚙️ {setting.description or setting.key}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin_setting_edit_{setting.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 К настройкам", callback_data="admin_settings")
    )
    
    return builder.as_markup()


def admin_setting_edit_kb(setting) -> InlineKeyboardMarkup:
    """Клавиатура редактирования конкретной настройки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить значение", callback_data=f"admin_setting_change_{setting.id}")
    )
    
    # Для boolean настроек добавляем быстрые кнопки
    if setting.value_type == "bool":
        current_value = setting.value.lower() in ("true", "1", "yes", "on")
        new_value = not current_value
        
        builder.row(
            InlineKeyboardButton(
                text=f"🔄 Переключить на {new_value}",
                callback_data=f"admin_setting_toggle_{setting.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_settings_category_{setting.category}")
    )
    
    return builder.as_markup()


def admin_setting_confirm_kb(setting_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения изменения настройки"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Сохранить", callback_data=f"admin_setting_confirm_{setting_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_setting_edit_{setting_id}")
    )
    
    return builder.as_markup()


def admin_settings_back_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата к настройкам"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔙 К настройкам", callback_data="admin_settings")
    )
    
    return builder.as_markup()