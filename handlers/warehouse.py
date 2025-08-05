"""Обработчики для управления складом товаров"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import ProductType
from utils.states import WarehouseAddProductStates, WarehouseGiveProductStates, WarehouseCreateCategoryStates
from utils.warehouse_templates import WarehouseMessages
from keyboards.warehouse_keyboards import (
    product_type_kb, warehouse_categories_select_kb, warehouse_products_select_kb,
    add_product_confirmation_kb, give_product_confirmation_kb, cancel_kb,
    back_to_warehouse_kb, warehouse_action_complete_kb, warehouse_all_products_kb,
    create_category_confirmation_kb, no_categories_warning_kb
)
from services.warehouse_service import WarehouseService


logger = logging.getLogger(__name__)
warehouse_router = Router()


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return user_id in settings.ADMIN_IDS


async def check_categories_exist(callback: CallbackQuery, session: AsyncSession) -> bool:
    """Проверить существование категорий и показать предупреждение если их нет"""
    from services.warehouse_service import WarehouseService
    
    warehouse_service = WarehouseService(session)
    has_categories = await warehouse_service.has_categories()
    
    if not has_categories:
        await callback.message.edit_text(
            WarehouseMessages.NO_CATEGORIES_WARNING,
            reply_markup=no_categories_warning_kb()
        )
        return False
    
    return True


# ========== ДОБАВЛЕНИЕ ТОВАРА ==========

@warehouse_router.callback_query(F.data == "warehouse_add_product")
async def start_add_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс добавления товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Проверяем существование категорий
    if not await check_categories_exist(callback, session):
        return
    
    warehouse_service = WarehouseService(session)
    categories = await warehouse_service.get_categories()
    
    await state.set_state(WarehouseAddProductStates.waiting_for_category)
    
    await callback.message.edit_text(
        WarehouseMessages.ADD_PRODUCT_START,
        reply_markup=warehouse_categories_select_kb(categories)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_select_category_"), WarehouseAddProductStates.waiting_for_category)
async def select_category(callback: CallbackQuery, state: FSMContext):
    """Выбрать категорию для товара"""
    category_id = int(callback.data.split("_")[-1])
    await state.update_data(category_id=category_id)
    await state.set_state(WarehouseAddProductStates.waiting_for_name)
    
    await callback.message.edit_text(
        WarehouseMessages.ADD_PRODUCT_NAME,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseAddProductStates.waiting_for_name)
async def enter_product_name(message: Message, state: FSMContext):
    """Ввод названия товара"""
    name = message.text.strip()
    
    if len(name) < 3:
        await message.answer(
            "❌ Название товара должно содержать минимум 3 символа. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(WarehouseAddProductStates.waiting_for_type)
    
    await message.answer(
        WarehouseMessages.ADD_PRODUCT_TYPE,
        reply_markup=product_type_kb()
    )


@warehouse_router.callback_query(F.data.startswith("warehouse_type_"), WarehouseAddProductStates.waiting_for_type)
async def select_product_type(callback: CallbackQuery, state: FSMContext):
    """Выбрать тип товара"""
    product_type = callback.data.split("_")[-1]
    await state.update_data(product_type=product_type)
    await state.set_state(WarehouseAddProductStates.waiting_for_duration)
    
    await callback.message.edit_text(
        WarehouseMessages.ADD_PRODUCT_DURATION,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseAddProductStates.waiting_for_duration)
async def enter_duration(message: Message, state: FSMContext):
    """Ввод длительности товара"""
    duration = message.text.strip()
    
    if len(duration) < 1:
        await message.answer(
            "❌ Длительность не может быть пустой. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    data = await state.get_data()
    product_type = data["product_type"]
    
    await state.update_data(duration=duration)
    await state.set_state(WarehouseAddProductStates.waiting_for_content)
    
    # Выбираем сообщение в зависимости от типа товара
    if product_type == ProductType.ACCOUNT.value:
        message_text = WarehouseMessages.ADD_PRODUCT_CONTENT_ACCOUNT
    elif product_type == ProductType.KEY.value:
        message_text = WarehouseMessages.ADD_PRODUCT_CONTENT_KEY
    else:  # PROMO
        message_text = WarehouseMessages.ADD_PRODUCT_CONTENT_PROMO
    
    await message.answer(message_text, reply_markup=cancel_kb())


@warehouse_router.message(WarehouseAddProductStates.waiting_for_content)
async def enter_content(message: Message, state: FSMContext):
    """Ввод содержимого товара"""
    content = message.text.strip()
    data = await state.get_data()
    product_type = data["product_type"]
    
    # Валидация формата для аккаунтов
    if product_type == ProductType.ACCOUNT.value and ":" not in content:
        await message.answer(
            WarehouseMessages.ERROR_INVALID_CONTENT_FORMAT,
            reply_markup=cancel_kb()
        )
        return
    
    if len(content) < 1:
        await message.answer(
            "❌ Содержимое не может быть пустым. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(content=content)
    await state.set_state(WarehouseAddProductStates.waiting_for_price)
    
    await message.answer(
        WarehouseMessages.ADD_PRODUCT_PRICE,
        reply_markup=cancel_kb()
    )


@warehouse_router.message(WarehouseAddProductStates.waiting_for_price)
async def enter_price(message: Message, state: FSMContext, session: AsyncSession):
    """Ввод цены товара"""
    try:
        price = float(message.text.strip().replace(",", "."))
        
        if price <= 0:
            await message.answer(
                "❌ Цена должна быть больше 0. Попробуйте еще раз:",
                reply_markup=cancel_kb()
            )
            return
        
        if price > 100000:
            await message.answer(
                "❌ Цена не может превышать 100,000₽. Попробуйте еще раз:",
                reply_markup=cancel_kb()
            )
            return
        
    except ValueError:
        await message.answer(
            WarehouseMessages.ERROR_INVALID_PRICE,
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(price=price)
    await state.set_state(WarehouseAddProductStates.waiting_for_confirmation)
    
    # Получаем все данные для показа
    data = await state.get_data()
    warehouse_service = WarehouseService(session)
    
    # Получаем категорию
    categories = await warehouse_service.get_categories()
    category = next((c for c in categories if c.id == data["category_id"]), None)
    category_name = category.name if category else "Неизвестная категория"
    
    # Получаем превью содержимого
    content_preview = WarehouseMessages.get_content_preview(
        data["content"], 
        data["product_type"]
    )
    
    product_type_display = WarehouseMessages.get_product_type_display(data["product_type"])
    
    confirmation_text = WarehouseMessages.ADD_PRODUCT_CONFIRMATION.format(
        name=data["name"],
        category=category_name,
        product_type=product_type_display,
        duration=data["duration"],
        price=price,
        content_preview=content_preview
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=add_product_confirmation_kb()
    )


@warehouse_router.callback_query(F.data == "warehouse_confirm_add_product", WarehouseAddProductStates.waiting_for_confirmation)
async def confirm_add_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить добавление товара"""
    data = await state.get_data()
    warehouse_service = WarehouseService(session)
    
    # Валидируем данные
    is_valid, error_message = await warehouse_service.validate_product_data(
        name=data["name"],
        category_id=data["category_id"],
        product_type=data["product_type"],
        duration=data["duration"],
        content=data["content"],
        price=data["price"]
    )
    
    if not is_valid:
        await callback.message.edit_text(
            f"❌ Ошибка валидации: {error_message}",
            reply_markup=back_to_warehouse_kb()
        )
        await state.clear()
        return
    
    # Добавляем товар
    product = await warehouse_service.add_product(
        name=data["name"],
        category_id=data["category_id"],
        product_type=data["product_type"],
        duration=data["duration"],
        content=data["content"],
        price=data["price"],
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    if product:
        success_text = WarehouseMessages.ADD_PRODUCT_SUCCESS.format(
            name=product.name,
            id=product.id,
            price=product.price
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при добавлении товара. Попробуйте еще раз.",
            reply_markup=back_to_warehouse_kb()
        )
    
    await state.clear()
    await callback.answer()


# ========== ВЫДАЧА ТОВАРА ==========

@warehouse_router.callback_query(F.data == "warehouse_give_product")
async def start_give_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс выдачи товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Проверяем существование категорий
    if not await check_categories_exist(callback, session):
        return
    
    warehouse_service = WarehouseService(session)
    products = await warehouse_service.get_available_products()
    
    if not products:
        await callback.message.edit_text(
            "❌ Нет доступных товаров для выдачи.",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    await state.set_state(WarehouseGiveProductStates.waiting_for_product)
    
    await callback.message.edit_text(
        WarehouseMessages.GIVE_PRODUCT_START,
        reply_markup=warehouse_products_select_kb(products)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_select_product_"), WarehouseGiveProductStates.waiting_for_product)
async def select_product_to_give(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбрать товар для выдачи"""
    product_id = int(callback.data.split("_")[-1])
    warehouse_service = WarehouseService(session)
    
    product = await warehouse_service.get_product_with_category(product_id)
    if not product:
        await callback.message.edit_text(
            WarehouseMessages.ERROR_PRODUCT_NOT_FOUND,
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    if not product.is_unlimited and product.stock_quantity <= 0:
        await callback.message.edit_text(
            WarehouseMessages.ERROR_NO_STOCK,
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    await state.update_data(product_id=product_id)
    await state.set_state(WarehouseGiveProductStates.waiting_for_user)
    
    stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
    
    give_user_text = WarehouseMessages.GIVE_PRODUCT_USER.format(
        product_name=product.name,
        price=product.price,
        stock=stock_display
    )
    
    await callback.message.edit_text(
        give_user_text,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseGiveProductStates.waiting_for_user)
async def enter_user_to_give(message: Message, state: FSMContext, session: AsyncSession):
    """Ввод пользователя для выдачи товара"""
    identifier = message.text.strip()
    warehouse_service = WarehouseService(session)
    
    # Поиск пользователя
    user = await warehouse_service.find_user_by_username_or_id(identifier)
    if not user:
        await message.answer(
            WarehouseMessages.ERROR_USER_NOT_FOUND,
            reply_markup=cancel_kb()
        )
        return
    
    # Получаем данные товара
    data = await state.get_data()
    product = await warehouse_service.get_product_with_category(data["product_id"])
    
    if not product:
        await message.answer(
            WarehouseMessages.ERROR_PRODUCT_NOT_FOUND,
            reply_markup=back_to_warehouse_kb()
        )
        await state.clear()
        return
    
    await state.update_data(
        recipient_id=user.id,
        recipient_username=user.username or user.first_name or str(user.id)
    )
    await state.set_state(WarehouseGiveProductStates.waiting_for_confirmation)
    
    recipient_display = f"@{user.username}" if user.username else user.first_name or f"ID: {user.id}"
    
    confirmation_text = WarehouseMessages.GIVE_PRODUCT_CONFIRMATION.format(
        product_name=product.name,
        price=product.price,
        recipient=recipient_display,
        content=product.digital_content or "Не указано"
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=give_product_confirmation_kb()
    )


@warehouse_router.callback_query(F.data == "warehouse_confirm_give_product", WarehouseGiveProductStates.waiting_for_confirmation)
async def confirm_give_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить выдачу товара"""
    
    data = await state.get_data()
    warehouse_service = WarehouseService(session)
    
    # Выдаем товар
    success, content, updated_product = await warehouse_service.give_product(
        product_id=data["product_id"],
        recipient_id=data["recipient_id"],
        recipient_username=data["recipient_username"],
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    if not success:
        await callback.message.edit_text(
            "❌ Ошибка при выдаче товара. Возможно, товар закончился.",
            reply_markup=back_to_warehouse_kb()
        )
        await state.clear()
        return
    
    # Сообщение админу
    new_stock = "∞" if updated_product.is_unlimited else str(updated_product.stock_quantity)
    recipient_display = f"@{data['recipient_username']}" if data['recipient_username'] else f"ID: {data['recipient_id']}"
    
    success_text = WarehouseMessages.GIVE_PRODUCT_SUCCESS.format(
        product_name=updated_product.name,
        recipient=recipient_display,
        new_stock=new_stock
    )
    
    await callback.message.edit_text(
        success_text,
        reply_markup=warehouse_action_complete_kb()
    )
    
    # Уведомление пользователю
    try:
        product_type_display = WarehouseMessages.get_product_type_display(updated_product.product_type)
        
        user_notification = WarehouseMessages.GIVE_PRODUCT_USER_NOTIFICATION.format(
            product_name=updated_product.name,
            product_type_display=product_type_display,
            duration=updated_product.duration or "Не указана",
            content=content
        )
        
        await callback.bot.send_message(
            chat_id=data["recipient_id"],
            text=user_notification
        )
        
    except Exception as e:
        logger.error(f"Failed to send notification to user {data['recipient_id']}: {e}")
    
    await state.clear()
    await callback.answer()


# ========== СОЗДАНИЕ КАТЕГОРИИ ==========

@warehouse_router.callback_query(F.data == "warehouse_create_category")
async def start_create_category(callback: CallbackQuery, state: FSMContext):
    """Начать процесс создания категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await state.set_state(WarehouseCreateCategoryStates.waiting_for_name)
    
    await callback.message.edit_text(
        WarehouseMessages.CREATE_CATEGORY_START,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseCreateCategoryStates.waiting_for_name)
async def enter_category_name(message: Message, state: FSMContext, session: AsyncSession):
    """Ввод названия категории"""
    name = message.text.strip()
    warehouse_service = WarehouseService(session)
    
    # Валидация имени категории
    is_valid, error_message = await warehouse_service.validate_category_data(name)
    if not is_valid:
        await message.answer(
            f"❌ {error_message}\n\nПопробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(WarehouseCreateCategoryStates.waiting_for_description)
    
    await message.answer(
        WarehouseMessages.CREATE_CATEGORY_DESCRIPTION,
        reply_markup=cancel_kb()
    )


@warehouse_router.message(WarehouseCreateCategoryStates.waiting_for_description)
async def enter_category_description(message: Message, state: FSMContext):
    """Ввод описания категории"""
    description = message.text.strip()
    
    # Если отправили "-", то пропускаем описание
    if description == "-":
        description = None
    
    data = await state.get_data()
    await state.update_data(description=description)
    await state.set_state(WarehouseCreateCategoryStates.waiting_for_confirmation)
    
    confirmation_text = WarehouseMessages.CREATE_CATEGORY_CONFIRMATION.format(
        name=data["name"],
        description=description or "Не указано"
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=create_category_confirmation_kb()
    )


@warehouse_router.callback_query(F.data == "warehouse_confirm_create_category", WarehouseCreateCategoryStates.waiting_for_confirmation)
async def confirm_create_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить создание категории"""
    data = await state.get_data()
    warehouse_service = WarehouseService(session)
    
    # Создаем категорию
    category = await warehouse_service.create_category(
        name=data["name"],
        description=data.get("description"),
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    if category:
        success_text = WarehouseMessages.CREATE_CATEGORY_SUCCESS.format(
            name=category.name,
            id=category.id,
            description=category.description or "Не указано"
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
        
        logger.info(f"WAREHOUSE: Category '{category.name}' created by admin {callback.from_user.id}")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при создании категории. Возможно, категория с таким именем уже существует.",
            reply_markup=back_to_warehouse_kb()
        )
    
    await state.clear()
    await callback.answer()


# ========== ОБНОВЛЕННЫЕ ОБРАБОТЧИКИ ==========

@warehouse_router.callback_query(F.data == "warehouse_all_products")  
async def warehouse_all_products_new(callback: CallbackQuery, session: AsyncSession):
    """Показать все товары с управлением"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    warehouse_service = WarehouseService(session)
    products = await warehouse_service.get_available_products()
    
    if not products:
        await callback.message.edit_text(
            "📦 <b>Все товары</b>\n\n❌ Товары не найдены.",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    await callback.message.edit_text(
        f"📦 <b>Все товары</b>\n\nВсего товаров: {len(products)}",
        reply_markup=warehouse_all_products_kb(products)
    )
    await callback.answer()


# ========== ОБЩИЕ ОБРАБОТЧИКИ ==========

@warehouse_router.callback_query(F.data == "warehouse_cancel")
async def cancel_warehouse_action(callback: CallbackQuery, state: FSMContext):
    """Отменить текущее действие на складе"""
    await state.clear()
    
    # Возвращаемся к меню склада
    from keyboards.inline_keyboards import warehouse_menu_kb
    
    await callback.message.edit_text(
        "🏪 <b>Склад товаров</b>\n\n"
        "Управление товарами и их выдача:",
        reply_markup=warehouse_menu_kb()
    )
    await callback.answer("❌ Действие отменено")


# Обработчики кнопок "нет товаров" и других служебных
@warehouse_router.callback_query(F.data == "warehouse_no_products")
async def no_products_handler(callback: CallbackQuery):
    """Обработчик для случая отсутствия товаров"""
    await callback.answer("❌ Нет доступных товаров", show_alert=True)


# Обработчик удален - не должен перехватывать все сообщения
# Все FSM состояния имеют свои специфичные обработчики