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
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить еще", callback_data="warehouse_add_product"),
        InlineKeyboardButton(text="🎯 Выдать товар", callback_data="warehouse_give_product")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К складу", callback_data="warehouse_menu")
    )
    
    return builder.as_markup()