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
    """Админ меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders"),
        InlineKeyboardButton(text="🛍 Товары", callback_data="admin_products")
    )
    builder.row(
        InlineKeyboardButton(text="📂 Категории", callback_data="admin_categories"),
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
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