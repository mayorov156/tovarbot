"""Обработчики для управления складом товаров"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import ProductType
from utils.states import WarehouseAddProductStates, WarehouseGiveProductStates, WarehouseCreateCategoryStates, WarehouseMassAddStates, WarehouseQuickAddStates
from utils.warehouse_templates import WarehouseMessages
from keyboards.warehouse_keyboards import (
    product_type_kb, warehouse_categories_select_kb, warehouse_products_select_kb,
    add_product_confirmation_kb, give_product_confirmation_kb, cancel_kb,
    back_to_warehouse_kb, warehouse_action_complete_kb, warehouse_all_products_kb,
    create_category_confirmation_kb, no_categories_warning_kb, mass_add_confirmation_kb
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


# ========== МАССОВОЕ ДОБАВЛЕНИЕ ТОВАРОВ ==========

@warehouse_router.callback_query(F.data == "warehouse_mass_add")
async def start_mass_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс массового добавления товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Проверяем существование категорий
    if not await check_categories_exist(callback, session):
        return
    
    warehouse_service = WarehouseService(session)
    categories = await warehouse_service.get_categories()
    
    await state.set_state(WarehouseMassAddStates.waiting_for_category)
    
    await callback.message.edit_text(
        WarehouseMessages.MASS_ADD_START,
        reply_markup=warehouse_categories_select_kb(categories)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_select_category_"), WarehouseMassAddStates.waiting_for_category)
async def mass_add_select_category(callback: CallbackQuery, state: FSMContext):
    """Выбрать категорию для массового добавления"""
    category_id = int(callback.data.split("_")[-1])
    
    await state.update_data(category_id=category_id)
    await state.set_state(WarehouseMassAddStates.waiting_for_name)
    
    await callback.message.edit_text(
        WarehouseMessages.MASS_ADD_NAME,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseMassAddStates.waiting_for_name)
async def mass_add_enter_name(message: Message, state: FSMContext):
    """Ввод базового названия для массового добавления"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer(
            "❌ Название должно содержать минимум 2 символа. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(WarehouseMassAddStates.waiting_for_type)
    
    await message.answer(
        WarehouseMessages.MASS_ADD_TYPE,
        reply_markup=product_type_kb()
    )


@warehouse_router.callback_query(F.data.startswith("product_type_"), WarehouseMassAddStates.waiting_for_type)
async def mass_add_select_type(callback: CallbackQuery, state: FSMContext):
    """Выбрать тип товара для массового добавления"""
    product_type = callback.data.split("_")[-1]
    
    await state.update_data(product_type=product_type)
    await state.set_state(WarehouseMassAddStates.waiting_for_duration)
    
    await callback.message.edit_text(
        WarehouseMessages.MASS_ADD_DURATION,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseMassAddStates.waiting_for_duration)  
async def mass_add_enter_duration(message: Message, state: FSMContext):
    """Ввод длительности для массового добавления"""
    duration = message.text.strip()
    
    await state.update_data(duration=duration)
    await state.set_state(WarehouseMassAddStates.waiting_for_price)
    
    await message.answer(
        WarehouseMessages.MASS_ADD_PRICE,
        reply_markup=cancel_kb()
    )


@warehouse_router.message(WarehouseMassAddStates.waiting_for_price)
async def mass_add_enter_price(message: Message, state: FSMContext):
    """Ввод цены для массового добавления"""
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            WarehouseMessages.ERROR_INVALID_PRICE + "\n\nПопробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    data = await state.get_data()
    product_type = data["product_type"]
    
    # Генерируем сообщение с форматом контента
    if product_type == ProductType.ACCOUNT.value:
        content_format = "Формат: <code>логин:пароль</code>\n\nПример:\n<code>user1@mail.com:password123\nuser2@mail.com:password456</code>"
    elif product_type == ProductType.KEY.value:
        content_format = "Формат: <code>ключ активации</code>\n\nПример:\n<code>XXXX-XXXX-XXXX-XXXX\nYYYY-YYYY-YYYY-YYYY</code>"
    else:  # PROMO
        content_format = "Формат: <code>промокод</code>\n\nПример:\n<code>PROMO2024\nDISCOUNT50</code>"
    
    await state.update_data(price=price)
    await state.set_state(WarehouseMassAddStates.waiting_for_content)
    
    await message.answer(
        WarehouseMessages.MASS_ADD_CONTENT.format(content_format=content_format),
        reply_markup=cancel_kb()
    )


@warehouse_router.message(WarehouseMassAddStates.waiting_for_content)
async def mass_add_enter_content(message: Message, state: FSMContext, session: AsyncSession):
    """Ввод контента для массового добавления"""
    content_text = message.text.strip()
    
    if not content_text:
        await message.answer(
            "❌ Контент не может быть пустым. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    data = await state.get_data()
    warehouse_service = WarehouseService(session)
    
    # Парсим строки контента
    content_lines = warehouse_service.parse_content_lines(content_text, data["product_type"])
    
    if not content_lines:
        await message.answer(
            "❌ Не найдено валидных строк контента. Проверьте формат и попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    # Получаем название категории
    category = await warehouse_service.get_category_by_id(data["category_id"])
    category_name = category.name if category else "Неизвестная"
    
    # Переводим тип товара на русский
    type_names = {
        ProductType.ACCOUNT.value: "Аккаунт (логин/пароль)",
        ProductType.KEY.value: "Ключ активации", 
        ProductType.PROMO.value: "Промокод"
    }
    
    await state.update_data(
        content_lines=content_lines,
        category_name=category_name
    )
    await state.set_state(WarehouseMassAddStates.waiting_for_confirmation)
    
    confirmation_text = WarehouseMessages.MASS_ADD_CONFIRMATION.format(
        name=data["name"],
        category=category_name,
        product_type=type_names.get(data["product_type"], data["product_type"]),
        duration=data["duration"],
        price=data["price"],
        count=len(content_lines)
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=mass_add_confirmation_kb()
    )


@warehouse_router.callback_query(F.data == "warehouse_confirm_mass_add", WarehouseMassAddStates.waiting_for_confirmation)
async def confirm_mass_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить массовое добавление товаров"""
    data = await state.get_data()
    warehouse_service = WarehouseService(session)
    
    # Массовое добавление товаров
    products = await warehouse_service.mass_add_products(
        base_name=data["name"],
        category_id=data["category_id"],
        product_type=data["product_type"],
        duration=data["duration"],
        price=data["price"],
        content_lines=data["content_lines"],
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    if products:
        total_value = len(products) * data["price"]
        
        success_text = WarehouseMessages.MASS_ADD_SUCCESS.format(
            count=len(products),
            name=data["name"],
            category=data["category_name"],
            total_value=total_value
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
        
        logger.info(f"WAREHOUSE: Mass added {len(products)} products by admin {callback.from_user.id}")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при массовом добавлении товаров. Попробуйте еще раз.",
            reply_markup=back_to_warehouse_kb()
        )
    
    await state.clear()
    await callback.answer()


# ========== БЫСТРОЕ ДОБАВЛЕНИЕ ТОВАРА ==========

@warehouse_router.callback_query(F.data == "warehouse_quick_add")
async def start_quick_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать быстрое добавление товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Проверяем существование категорий
    if not await check_categories_exist(callback, session):
        return
    
    warehouse_service = WarehouseService(session)
    categories = await warehouse_service.get_categories()
    
    await state.set_state(WarehouseQuickAddStates.waiting_for_category)
    
    await callback.message.edit_text(
        WarehouseMessages.QUICK_ADD_START,
        reply_markup=warehouse_categories_select_kb(categories)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_select_category_"), WarehouseQuickAddStates.waiting_for_category)
async def quick_add_select_category(callback: CallbackQuery, state: FSMContext):
    """Выбрать категорию для быстрого добавления"""
    category_id = int(callback.data.split("_")[-1])
    
    await state.update_data(category_id=category_id)
    await state.set_state(WarehouseQuickAddStates.waiting_for_all_data)
    
    await callback.message.edit_text(
        WarehouseMessages.QUICK_ADD_DATA,
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseQuickAddStates.waiting_for_all_data)
async def quick_add_enter_data(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка всех данных для быстрого добавления"""
    data_text = message.text.strip()
    
    warehouse_service = WarehouseService(session)
    
    # Парсим данные
    is_valid, parsed_data = warehouse_service.parse_quick_add_data(data_text)
    
    if not is_valid:
        await message.answer(
            f"❌ {parsed_data['error']}\n\nПопробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    # Получаем данные состояния
    state_data = await state.get_data()
    category_id = state_data["category_id"]
    
    # Добавляем товар сразу без подтверждения (быстрое добавление)
    product = await warehouse_service.add_product(
        name=parsed_data['name'],
        category_id=category_id,
        product_type=parsed_data['product_type'],
        duration=parsed_data['duration'],
        price=parsed_data['price'],
        content=parsed_data['content'],
        admin_id=message.from_user.id,
        admin_username=message.from_user.username
    )
    
    if product:
        # Получаем название категории
        category = await warehouse_service.get_category_by_id(category_id)
        category_name = category.name if category else "Неизвестная"
        
        # Переводим тип товара на русский
        type_names = {
            ProductType.ACCOUNT.value: "Аккаунт (логин/пароль)",
            ProductType.KEY.value: "Ключ активации", 
            ProductType.PROMO.value: "Промокод"
        }
        
        success_text = WarehouseMessages.QUICK_ADD_SUCCESS.format(
            name=product.name,
            category=category_name,
            product_type=type_names.get(product.product_type, product.product_type),
            duration=product.duration,
            price=product.price
        )
        
        await message.answer(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
        
        logger.info(f"WAREHOUSE: Quick added product '{product.name}' by admin {message.from_user.id}")
    else:
        await message.answer(
            "❌ Ошибка при добавлении товара. Попробуйте еще раз.",
            reply_markup=back_to_warehouse_kb()
        )
    
    await state.clear()


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