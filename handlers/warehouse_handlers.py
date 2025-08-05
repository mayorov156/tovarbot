"""Обработчики для управления складом товаров"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import ProductType
from utils.states import WarehouseAddProductStates, WarehouseGiveProductStates, WarehouseCreateCategoryStates, WarehouseMassAddStates, WarehouseQuickAddStates, WarehouseEditProductStates, WarehouseQuickGiveStates
from utils.warehouse_templates import WarehouseMessages
from keyboards.warehouse_keyboards import (
    product_type_kb, warehouse_categories_select_kb, warehouse_products_select_kb,
    add_product_confirmation_kb, give_product_confirmation_kb, cancel_kb,
    back_to_warehouse_kb, warehouse_action_complete_kb, warehouse_all_products_kb,
    create_category_confirmation_kb, no_categories_warning_kb, mass_add_confirmation_kb,
    edit_product_fields_kb, edit_product_type_kb, edit_product_confirmation_kb,
    warehouse_add_menu_kb, warehouse_quick_master_kb, category_created_kb,
    warehouse_categories_compact_kb, warehouse_category_products_kb
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
        
        # Отправляем мануал, если он есть у категории
        if updated_product.category and updated_product.category.manual_url:
            manual_notification = WarehouseMessages.MANUAL_NOTIFICATION.format(
                product_name=updated_product.name,
                manual_url=updated_product.category.manual_url
            )
            
            await callback.bot.send_message(
                chat_id=data["recipient_id"],
                text=manual_notification
            )
            
            logger.info(f"WAREHOUSE: Sent manual to user {data['recipient_id']} for product '{updated_product.name}': {updated_product.category.manual_url}")
        
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
    
    await state.update_data(description=description)
    await state.set_state(WarehouseCreateCategoryStates.waiting_for_manual_url)
    
    await message.answer(
        WarehouseMessages.CREATE_CATEGORY_MANUAL,
        reply_markup=cancel_kb()
    )


@warehouse_router.message(WarehouseCreateCategoryStates.waiting_for_manual_url)
async def enter_category_manual_url(message: Message, state: FSMContext):
    """Ввод ссылки на мануал для категории"""
    manual_url = message.text.strip()
    
    # Если отправили "-", то пропускаем мануал
    if manual_url == "-":
        manual_url = None
    
    data = await state.get_data()
    await state.update_data(manual_url=manual_url)
    await state.set_state(WarehouseCreateCategoryStates.waiting_for_confirmation)
    
    confirmation_text = WarehouseMessages.CREATE_CATEGORY_CONFIRMATION.format(
        name=data["name"],
        description=data.get("description") or "Не указано",
        manual_url=manual_url or "Не указано"
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
        manual_url=data.get("manual_url"),
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    if category:
        success_text = WarehouseMessages.CREATE_CATEGORY_SUCCESS.format(
            name=category.name,
            id=category.id,
            description=category.description or "Не указано",
            manual_url=category.manual_url or "Не указано"
        )
        
        success_text += "\n\n💡 <b>Что делать дальше?</b>\nТеперь можно добавить товары в созданную категорию."
        
        await callback.message.edit_text(
            success_text,
            reply_markup=category_created_kb(category.id)
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


@warehouse_router.callback_query(F.data.startswith("warehouse_type_"), WarehouseMassAddStates.waiting_for_type)
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
    
    # Массовое добавление товаров с отчетом
    products, report = await warehouse_service.mass_add_products(
        base_name=data["name"],
        category_id=data["category_id"],
        product_type=data["product_type"],
        duration=data["duration"],
        price=data["price"],
        content_lines=data["content_lines"],
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    # Получаем данные остатков по категории
    category_products = await warehouse_service.get_products_by_category(data["category_id"])
    category_stock = sum(p.stock_quantity for p in category_products if not p.is_unlimited)
    
    # Формируем отчет
    if report['successful'] > 0:
        total_value = len(products) * data["price"]
        
        success_text = f"✅ <b>Массовое добавление завершено!</b>\n\n"
        success_text += f"📦 <b>Результат:</b>\n"
        success_text += f"✅ Добавлено товаров: {report['successful']}\n"
        success_text += f"📋 Всего строк обработано: {report['total_lines']}\n"
        success_text += f"💰 Общая стоимость: {total_value:.2f}₽\n\n"
        
        success_text += f"📂 <b>Итоговый остаток по категории:</b>\n"
        success_text += f"'{data['category_name']}': {category_stock} шт.\n\n"
        
        # Показываем ошибки если есть
        if report['errors']:
            success_text += f"⚠️ <b>Ошибки ({len(report['errors'])}):</b>\n"
            # Показываем только первые 5 ошибок для экономии места
            for error in report['errors'][:5]:
                success_text += f"• {error}\n"
            if len(report['errors']) > 5:
                success_text += f"• ... и еще {len(report['errors']) - 5} ошибок\n"
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
        
        logger.info(f"WAREHOUSE: Mass added {len(products)} products by admin {callback.from_user.id}")
    else:
        # Если не добавлено ни одного товара
        error_text = f"❌ <b>Не удалось добавить товары</b>\n\n"
        error_text += f"📋 Всего строк: {report['total_lines']}\n"
        error_text += f"❌ Ошибок: {len(report['errors'])}\n\n"
        
        error_text += f"<b>Основные ошибки:</b>\n"
        for error in report['errors'][:10]:  # Показываем больше ошибок при полном провале
            error_text += f"• {error}\n"
        
        await callback.message.edit_text(
            error_text,
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


# ========== БЫСТРАЯ ВЫДАЧА ТОВАРА (ОБЪЕДИНЕННАЯ) ==========

@warehouse_router.callback_query(F.data == "warehouse_quick_give")
async def start_quick_give(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать быструю выдачу товара - объединенный интерфейс"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await state.set_state(WarehouseQuickGiveStates.waiting_for_search)
    
    await callback.message.edit_text(
        "⚡ <b>Быстрая выдача товара</b>\n\n"
        "Введите название товара для поиска или его ID:\n\n"
        "📌 <b>Примеры:</b>\n"
        "• <code>Netflix</code> - поиск по названию\n"
        "• <code>#123</code> - поиск по ID товара\n\n"
        "Будут показаны все подходящие товары с остатком > 0.",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.message(WarehouseQuickGiveStates.waiting_for_search)
async def quick_give_search_product(message: Message, state: FSMContext, session: AsyncSession):
    """Поиск товара для быстрой выдачи"""
    search_text = message.text.strip()
    warehouse_service = WarehouseService(session)
    
    # Поиск товаров
    if search_text.startswith("#"):
        # Поиск по ID
        try:
            product_id = int(search_text[1:])
            product = await warehouse_service.get_product_with_category(product_id)
            if product and (product.is_unlimited or product.stock_quantity > 0):
                products = [product]
            else:
                products = []
        except ValueError:
            products = []
    else:
        # Поиск по названию
        all_products = await warehouse_service.get_available_products()
        products = [p for p in all_products if search_text.lower() in p.name.lower()]
    
    if not products:
        await message.answer(
            "❌ Товары не найдены или нет в наличии.\n\n"
            "Попробуйте другой запрос:",
            reply_markup=cancel_kb()
        )
        return
    
    # Если найден только один товар - переходим к выбору пользователя
    if len(products) == 1:
        product = products[0]
        await state.update_data(product_id=product.id)
        await state.set_state(WarehouseQuickGiveStates.waiting_for_user)
        
        stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
        
        await message.answer(
            f"✅ <b>Найден товар:</b>\n\n"
            f"📦 <b>Название:</b> {product.name}\n"
            f"💰 <b>Цена:</b> {product.price:.2f}₽\n"
            f"📊 <b>Остаток:</b> {stock_display} шт.\n\n"
            f"👤 Введите username пользователя (без @) или его Telegram ID:",
            reply_markup=cancel_kb()
        )
        return
    
    # Если найдено несколько товаров - показываем список
    await state.set_state(WarehouseQuickGiveStates.waiting_for_search)
    
    text = f"🔍 <b>Найдено товаров: {len(products)}</b>\n\n"
    for i, product in enumerate(products[:10], 1):  # Показываем максимум 10
        stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
        text += f"{i}. <b>{product.name}</b> (#{product.id})\n"
        text += f"   💰 {product.price:.2f}₽ • 📊 {stock_display} шт.\n\n"
    
    if len(products) > 10:
        text += f"... и еще {len(products) - 10} товаров\n\n"
    
    text += "Введите <b>номер товара</b> или <b>ID</b> для выдачи:"
    
    # Сохраняем список найденных товаров
    await state.update_data(found_products=[p.id for p in products])
    
    await message.answer(text, reply_markup=cancel_kb())


@warehouse_router.message(WarehouseQuickGiveStates.waiting_for_user)
async def quick_give_select_user(message: Message, state: FSMContext, session: AsyncSession):
    """Выбор пользователя для быстрой выдачи"""
    data = await state.get_data()
    
    # Если это номер товара из списка или повторный поиск
    if "found_products" in data:
        try:
            # Пробуем распарсить как номер товара из списка
            if message.text.strip().isdigit():
                product_index = int(message.text.strip()) - 1
                if 0 <= product_index < len(data["found_products"]):
                    product_id = data["found_products"][product_index]
                    await state.update_data(product_id=product_id)
                    # Удаляем список найденных товаров
                    state_data = await state.get_data()
                    state_data.pop("found_products", None)
                    await state.set_data(state_data)
                else:
                    await message.answer("❌ Неверный номер товара. Попробуйте еще раз:", reply_markup=cancel_kb())
                    return
            elif message.text.strip().startswith("#"):
                # Поиск по ID
                product_id = int(message.text.strip()[1:])
                await state.update_data(product_id=product_id)
                # Удаляем список найденных товаров
                state_data = await state.get_data()
                state_data.pop("found_products", None)
                await state.set_data(state_data)
            else:
                await message.answer("❌ Введите номер товара из списка или ID товара (например: #123):", reply_markup=cancel_kb())
                return
                
            # Получаем выбранный товар
            warehouse_service = WarehouseService(session)
            product = await warehouse_service.get_product_with_category(product_id)
            
            if not product or (not product.is_unlimited and product.stock_quantity <= 0):
                await message.answer("❌ Товар не найден или закончился. Попробуйте еще раз:", reply_markup=cancel_kb())
                await state.set_state(WarehouseQuickGiveStates.waiting_for_search)
                return
            
            stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
            
            await message.answer(
                f"✅ <b>Выбран товар:</b>\n\n"
                f"📦 <b>Название:</b> {product.name}\n"
                f"💰 <b>Цена:</b> {product.price:.2f}₽\n"
                f"📊 <b>Остаток:</b> {stock_display} шт.\n\n"
                f"👤 Введите username пользователя (без @) или его Telegram ID:",
                reply_markup=cancel_kb()
            )
            return
            
        except (ValueError, IndexError):
            await message.answer("❌ Неверный формат. Введите номер товара из списка:", reply_markup=cancel_kb())
            return
    
    # Поиск пользователя
    identifier = message.text.strip()
    warehouse_service = WarehouseService(session)
    
    user = await warehouse_service.find_user_by_username_or_id(identifier)
    if not user:
        await message.answer(
            WarehouseMessages.ERROR_USER_NOT_FOUND,
            reply_markup=cancel_kb()
        )
        return
    
    # Получаем данные товара
    product_id = data.get("product_id")
    product = await warehouse_service.get_product_with_category(product_id)
    
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
    await state.set_state(WarehouseQuickGiveStates.waiting_for_confirmation)
    
    recipient_display = f"@{user.username}" if user.username else user.first_name or f"ID: {user.id}"
    
    confirmation_text = f"⚡ <b>Подтверждение быстрой выдачи</b>\n\n" + WarehouseMessages.GIVE_PRODUCT_CONFIRMATION.format(
        product_name=product.name,
        price=product.price,
        recipient=recipient_display,
        content=product.digital_content or "Не указано"
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=give_product_confirmation_kb()
    )


@warehouse_router.callback_query(F.data == "warehouse_confirm_give_product", WarehouseQuickGiveStates.waiting_for_confirmation)
async def confirm_quick_give_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить быструю выдачу товара"""
    
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
    
    success_text = f"⚡ <b>Быстрая выдача завершена!</b>\n\n" + WarehouseMessages.GIVE_PRODUCT_SUCCESS.format(
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
        
        # Отправляем мануал, если он есть у категории
        if updated_product.category and updated_product.category.manual_url:
            manual_notification = WarehouseMessages.MANUAL_NOTIFICATION.format(
                product_name=updated_product.name,
                manual_url=updated_product.category.manual_url
            )
            
            await callback.bot.send_message(
                chat_id=data["recipient_id"],
                text=manual_notification
            )
            
            logger.info(f"WAREHOUSE: Sent manual to user {data['recipient_id']} for product '{updated_product.name}': {updated_product.category.manual_url}")
        
    except Exception as e:
        logger.error(f"Failed to send notification to user {data['recipient_id']}: {e}")
    
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


# ========== КОМПАКТНОЕ ОТОБРАЖЕНИЕ ТОВАРОВ ПО КАТЕГОРИЯМ ==========

@warehouse_router.callback_query(F.data == "warehouse_all_products_compact")
async def warehouse_all_products_compact(callback: CallbackQuery, session: AsyncSession):
    """Показать компактное отображение всех товаров по категориям"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    warehouse_service = WarehouseService(session)
    category_stats = await warehouse_service.get_category_stats()
    
    if not category_stats:
        await callback.message.edit_text(
            "📦 <b>Товары по категориям</b>\n\n❌ Категории не найдены.",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Подсчитываем общую статистику
    total_products = sum(cat['total_products'] for cat in category_stats)
    total_stock = sum(cat['total_stock'] for cat in category_stats)
    total_unlimited = sum(cat['unlimited_products'] for cat in category_stats)
    
    stock_display = ""
    if total_unlimited > 0:
        stock_display += f"∞x{total_unlimited}"
    if total_stock > 0:
        if stock_display:
            stock_display += f" + {total_stock}"
        else:
            stock_display = str(total_stock)
    
    if not stock_display:
        stock_display = "0"
    
    text = (
        f"📦 <b>Товары по категориям</b>\n\n"
        f"📊 <b>Общая статистика:</b>\n"
        f"• Категорий: {len(category_stats)}\n"
        f"• Товаров: {total_products}\n"
        f"• Остаток: {stock_display} шт.\n\n"
        f"Выберите категорию для просмотра товаров:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=warehouse_categories_compact_kb(category_stats)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_category_products_"))
async def warehouse_category_products_handler(callback: CallbackQuery, session: AsyncSession):
    """Показать товары в выбранной категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Парсим callback data
    parts = callback.data.split("_")
    category_id = int(parts[3])
    page = int(parts[4]) if len(parts) > 4 else 0
    
    warehouse_service = WarehouseService(session)
    
    # Получаем категорию
    category = await warehouse_service.get_category_by_id(category_id)
    if not category:
        await callback.message.edit_text(
            "❌ Категория не найдена",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Получаем товары в категории
    products = await warehouse_service.get_products_by_category(category_id)
    
    if not products:
        await callback.message.edit_text(
            f"📂 <b>Категория: {category.name}</b>\n\n❌ Товары в категории не найдены.",
            reply_markup=warehouse_categories_compact_kb([])  # Возвращаемся к списку категорий
        )
        return
    
    # Подсчитываем статистику для категории
    available_count = sum(1 for p in products if p.is_unlimited or p.stock_quantity > 0)
    total_stock = sum(p.stock_quantity for p in products if not p.is_unlimited)
    unlimited_count = sum(1 for p in products if p.is_unlimited)
    
    stock_display = ""
    if unlimited_count > 0:
        stock_display += f"∞x{unlimited_count}"
    if total_stock > 0:
        if stock_display:
            stock_display += f" + {total_stock}"
        else:
            stock_display = str(total_stock)
    
    if not stock_display:
        stock_display = "0"
    
    per_page = 3  # Меньше товаров на странице для лучшего отображения
    total_pages = (len(products) + per_page - 1) // per_page
    
    text = (
        f"📂 <b>Категория: {category.name}</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Всего товаров: {len(products)}\n"
        f"• Доступно: {available_count}\n"
        f"• Остаток: {stock_display} шт.\n\n"
    )
    
    if total_pages > 1:
        text += f"📄 Страница {page + 1} из {total_pages}\n\n"
    
    text += "Выберите товар для управления:"
    
    await callback.message.edit_text(
        text,
        reply_markup=warehouse_category_products_kb(products, category_id, category.name, page, per_page)
    )
    await callback.answer()


# ========== БЫСТРАЯ ВЫДАЧА ОТДЕЛЬНОГО ТОВАРА ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_give_single_"))
async def give_single_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Быстрая выдача конкретного товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split("_")[-1])
    warehouse_service = WarehouseService(session)
    
    product = await warehouse_service.get_product_with_category(product_id)
    if not product:
        await callback.message.edit_text(
            "❌ Товар не найден",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    if not product.is_unlimited and product.stock_quantity <= 0:
        await callback.message.edit_text(
            "❌ Товар закончился на складе",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Переходим к состоянию ввода пользователя
    await state.update_data(product_id=product_id)
    await state.set_state(WarehouseQuickGiveStates.waiting_for_user)
    
    stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
    
    await callback.message.edit_text(
        f"🎯 <b>Выдача товара</b>\n\n"
        f"📦 <b>Товар:</b> {product.name}\n"
        f"💰 <b>Цена:</b> {product.price:.2f}₽\n"
        f"📊 <b>Остаток:</b> {stock_display} шт.\n\n"
        f"👤 Введите username пользователя (без @) или его Telegram ID:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


# ========== РЕДАКТИРОВАНИЕ ТОВАРА ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_edit_"))
async def start_edit_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать редактирование товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split("_")[-1])
    warehouse_service = WarehouseService(session)
    
    product = await warehouse_service.get_product_with_category(product_id)
    if not product:
        await callback.message.edit_text(
            "❌ Товар не найден или удален",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(WarehouseEditProductStates.waiting_for_field_selection)
    
    # Формируем информацию о товаре
    stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
    product_type_display = WarehouseMessages.get_product_type_display(product.product_type)
    content_preview = WarehouseMessages.get_content_preview(product.digital_content or "", product.product_type)
    
    edit_text = WarehouseMessages.EDIT_PRODUCT_START.format(
        name=product.name,
        category=product.category.name if product.category else "Неизвестная",
        product_type_display=product_type_display,
        duration=product.duration or "Не указана",
        price=product.price,
        stock=stock_display,
        content_preview=content_preview
    )
    
    await callback.message.edit_text(
        edit_text,
        reply_markup=edit_product_fields_kb()
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("edit_field_"), WarehouseEditProductStates.waiting_for_field_selection)
async def select_edit_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбрать поле для редактирования"""
    field = callback.data.split("_")[-1]
    data = await state.get_data()
    product_id = data.get("product_id")
    
    warehouse_service = WarehouseService(session)
    product = await warehouse_service.get_product_with_category(product_id)
    
    if not product:
        await callback.message.edit_text(
            "❌ Товар не найден",
            reply_markup=back_to_warehouse_kb()
        )
        await state.clear()
        return
    
    await state.update_data(edit_field=field)
    
    if field == "name":
        await state.set_state(WarehouseEditProductStates.waiting_for_name)
        await callback.message.edit_text(
            WarehouseMessages.EDIT_PRODUCT_NAME.format(current_name=product.name),
            reply_markup=cancel_kb()
        )
    
    elif field == "type":
        await state.set_state(WarehouseEditProductStates.waiting_for_type)
        current_type_display = WarehouseMessages.get_product_type_display(product.product_type)
        await callback.message.edit_text(
            WarehouseMessages.EDIT_PRODUCT_TYPE.format(current_type=current_type_display),
            reply_markup=edit_product_type_kb()
        )
    
    elif field == "duration":
        await state.set_state(WarehouseEditProductStates.waiting_for_duration)
        await callback.message.edit_text(
            WarehouseMessages.EDIT_PRODUCT_DURATION.format(current_duration=product.duration or "Не указана"),
            reply_markup=cancel_kb()
        )
    
    elif field == "price":
        await state.set_state(WarehouseEditProductStates.waiting_for_price)
        await callback.message.edit_text(
            WarehouseMessages.EDIT_PRODUCT_PRICE.format(current_price=product.price),
            reply_markup=cancel_kb()
        )
    
    elif field == "content":
        await state.set_state(WarehouseEditProductStates.waiting_for_content)
        
        # Формируем сообщение в зависимости от типа товара
        product_type_display = WarehouseMessages.get_product_type_display(product.product_type)
        current_content_preview = WarehouseMessages.get_content_preview(product.digital_content or "", product.product_type)
        
        if product.product_type == ProductType.ACCOUNT.value:
            content_format_message = "Введите новые данные аккаунта в формате:\n<code>логин:пароль</code>"
        elif product.product_type == ProductType.KEY.value:
            content_format_message = "Введите новый ключ активации:\n<code>XXXX-XXXX-XXXX-XXXX</code>"
        else:  # PROMO
            content_format_message = "Введите новый промокод:\n<code>SAVE20OFF</code>"
        
        await callback.message.edit_text(
            WarehouseMessages.EDIT_PRODUCT_CONTENT.format(
                product_type_display=product_type_display,
                current_content_preview=current_content_preview,
                content_format_message=content_format_message
            ),
            reply_markup=cancel_kb()
        )
    
    await callback.answer()


@warehouse_router.message(WarehouseEditProductStates.waiting_for_name)
async def edit_product_name(message: Message, state: FSMContext, session: AsyncSession):
    """Редактировать название товара"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    new_name = message.text.strip()
    
    if len(new_name) < 3:
        await message.answer(
            "❌ Название товара должно содержать минимум 3 символа. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(new_name=new_name)
    await confirm_product_edit(message, state, session)


@warehouse_router.callback_query(F.data.startswith("edit_type_"), WarehouseEditProductStates.waiting_for_type)
async def edit_product_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Редактировать тип товара"""
    new_type = callback.data.split("_")[-1]
    
    await state.update_data(new_type=new_type)
    await confirm_product_edit(callback.message, state, session)
    await callback.answer()


@warehouse_router.message(WarehouseEditProductStates.waiting_for_duration)
async def edit_product_duration(message: Message, state: FSMContext, session: AsyncSession):
    """Редактировать длительность товара"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    new_duration = message.text.strip()
    
    if len(new_duration) < 1:
        await message.answer(
            "❌ Длительность не может быть пустой. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(new_duration=new_duration)
    await confirm_product_edit(message, state, session)


@warehouse_router.message(WarehouseEditProductStates.waiting_for_price)
async def edit_product_price(message: Message, state: FSMContext, session: AsyncSession):
    """Редактировать цену товара"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    try:
        new_price = float(message.text.strip().replace(",", "."))
        
        if new_price <= 0:
            await message.answer(
                "❌ Цена должна быть больше 0. Попробуйте еще раз:",
                reply_markup=cancel_kb()
            )
            return
        
        if new_price > 100000:
            await message.answer(
                "❌ Цена не может превышать 100,000₽. Попробуйте еще раз:",
                reply_markup=cancel_kb()
            )
            return
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат цены. Введите число (например: 299 или 99.99):",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(new_price=new_price)
    await confirm_product_edit(message, state, session)


@warehouse_router.message(WarehouseEditProductStates.waiting_for_content)
async def edit_product_content(message: Message, state: FSMContext, session: AsyncSession):
    """Редактировать содержимое товара"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    new_content = message.text.strip()
    data = await state.get_data()
    product_id = data.get("product_id")
    
    warehouse_service = WarehouseService(session)
    product = await warehouse_service.get_product_with_category(product_id)
    
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    # Валидация формата для аккаунтов
    if product.product_type == ProductType.ACCOUNT.value and ":" not in new_content:
        await message.answer(
            "❌ Для аккаунтов используйте формат 'логин:пароль'. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    if len(new_content) < 1:
        await message.answer(
            "❌ Содержимое не может быть пустым. Попробуйте еще раз:",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(new_content=new_content)
    await confirm_product_edit(message, state, session)


async def confirm_product_edit(message: Message, state: FSMContext, session: AsyncSession):
    """Показать подтверждение редактирования товара"""
    data = await state.get_data()
    product_id = data.get("product_id")
    
    warehouse_service = WarehouseService(session)
    product = await warehouse_service.get_product_with_category(product_id)
    
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    # Формируем список изменений
    changes = []
    if "new_name" in data and data["new_name"] != product.name:
        changes.append(f"🏷 Название: '{product.name}' → '{data['new_name']}'")
    
    if "new_type" in data and data["new_type"] != product.product_type:
        old_type_display = WarehouseMessages.get_product_type_display(product.product_type)
        new_type_display = WarehouseMessages.get_product_type_display(data["new_type"])
        changes.append(f"📦 Тип: '{old_type_display}' → '{new_type_display}'")
    
    if "new_duration" in data and data["new_duration"] != product.duration:
        changes.append(f"⏱ Длительность: '{product.duration or 'Не указана'}' → '{data['new_duration']}'")
    
    if "new_price" in data and data["new_price"] != product.price:
        changes.append(f"💰 Цена: {product.price}₽ → {data['new_price']}₽")
    
    if "new_content" in data and data["new_content"] != product.digital_content:
        old_preview = WarehouseMessages.get_content_preview(product.digital_content or "", product.product_type)
        new_preview = WarehouseMessages.get_content_preview(data["new_content"], product.product_type)
        changes.append(f"📋 Содержимое: '{old_preview}' → '{new_preview}'")
    
    if not changes:
        await message.answer(
            "❌ Изменения не обнаружены",
            reply_markup=back_to_warehouse_kb()
        )
        await state.clear()
        return
    
    changes_text = "\n".join(changes)
    
    await state.set_state(WarehouseEditProductStates.waiting_for_confirmation)
    
    confirmation_text = WarehouseMessages.EDIT_PRODUCT_CONFIRMATION.format(
        product_name=product.name,
        changes_text=changes_text
    )
    
    await message.answer(
        confirmation_text,
        reply_markup=edit_product_confirmation_kb()
    )


@warehouse_router.callback_query(F.data == "warehouse_confirm_edit_product", WarehouseEditProductStates.waiting_for_confirmation)
async def confirm_edit_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить редактирование товара"""
    data = await state.get_data()
    product_id = data.get("product_id")
    
    warehouse_service = WarehouseService(session)
    
    # Обновляем товар
    updated_product = await warehouse_service.update_product(
        product_id=product_id,
        name=data.get("new_name"),
        price=data.get("new_price"),
        product_type=data.get("new_type"),
        duration=data.get("new_duration"),
        digital_content=data.get("new_content"),
        admin_id=callback.from_user.id,
        admin_username=callback.from_user.username
    )
    
    if updated_product:
        # Показываем успешное обновление
        stock_display = "∞" if updated_product.is_unlimited else str(updated_product.stock_quantity)
        product_type_display = WarehouseMessages.get_product_type_display(updated_product.product_type)
        
        success_text = WarehouseMessages.EDIT_PRODUCT_SUCCESS.format(
            name=updated_product.name,
            category=updated_product.category.name if updated_product.category else "Неизвестная",
            product_type_display=product_type_display,
            duration=updated_product.duration or "Не указана",
            price=updated_product.price,
            stock=stock_display
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
        
        logger.info(f"WAREHOUSE: Product {product_id} edited by admin {callback.from_user.id}")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при обновлении товара. Попробуйте еще раз.",
            reply_markup=back_to_warehouse_kb()
        )
    
    await state.clear()
    await callback.answer()


# ========== УДАЛЕНИЕ ТОВАРА ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_delete_"))
async def delete_product_confirm(callback: CallbackQuery, session: AsyncSession):
    """Подтверждение удаления товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split("_")[-1])
    warehouse_service = WarehouseService(session)
    
    product = await warehouse_service.get_product_with_category(product_id)
    if not product:
        await callback.message.edit_text(
            "❌ Товар не найден",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
    
    confirmation_text = (
        f"⚠️ <b>Подтверждение удаления товара</b>\n\n"
        f"📦 <b>Название:</b> {product.name}\n"
        f"📂 <b>Категория:</b> {product.category.name if product.category else 'Неизвестная'}\n"
        f"💰 <b>Цена:</b> {product.price:.2f}₽\n"
        f"📊 <b>Остаток:</b> {stock_display} шт.\n\n"
        f"❓ <b>Вы уверены, что хотите удалить этот товар?</b>\n"
        f"Это действие нельзя отменить!"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"warehouse_confirm_delete_{product_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_all_products_compact")
    )
    
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_confirm_delete_"))
async def confirm_delete_product(callback: CallbackQuery, session: AsyncSession):
    """Окончательное удаление товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split("_")[-1])
    warehouse_service = WarehouseService(session)
    
    # Получаем товар перед удалением
    product = await warehouse_service.get_product_with_category(product_id)
    if not product:
        await callback.message.edit_text(
            "❌ Товар не найден",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    try:
        # Помечаем товар как неактивный (мягкое удаление)
        product.is_active = False
        
        # Логируем удаление
        await warehouse_service._log_warehouse_action(
            product_id=product_id,
            admin_id=callback.from_user.id,
            admin_username=callback.from_user.username,
            action="delete_product",
            quantity=0,
            description=f"Удален товар: {product.name}"
        )
        
        await session.commit()
        
        success_text = (
            f"✅ <b>Товар успешно удален!</b>\n\n"
            f"📦 <b>Название:</b> {product.name}\n"
            f"🆔 <b>ID:</b> #{product.id}\n"
            f"💰 <b>Цена:</b> {product.price:.2f}₽\n\n"
            f"Товар перемещен в архив и больше не доступен для заказа."
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_action_complete_kb()
        )
        
        logger.info(f"WAREHOUSE: Product {product_id} deleted by admin {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        await session.rollback()
        
        await callback.message.edit_text(
            "❌ Ошибка при удалении товара. Попробуйте еще раз.",
            reply_markup=back_to_warehouse_kb()
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


# ========== НОВЫЕ МЕНЮ И МАСТЕРЫ ==========

@warehouse_router.callback_query(F.data == "warehouse_add_menu")
async def warehouse_add_menu_callback(callback: CallbackQuery):
    """Показать меню способов добавления товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📥 <b>Добавить/Импортировать товары</b>\n\n"
        "Выберите способ добавления товаров на склад:",
        reply_markup=warehouse_add_menu_kb()
    )
    await callback.answer()


@warehouse_router.callback_query(F.data == "warehouse_quick_master")
async def warehouse_quick_master_callback(callback: CallbackQuery):
    """Показать быстрый мастер"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚡ <b>Быстрый мастер</b>\n\n"
        "Наиболее часто используемые действия:\n\n"
        "🎯 <b>Выдать товар</b> - быстро выдать товар пользователю\n"
        "⚡ <b>Быстро добавить</b> - добавить товар одним сообщением\n\n"
        "Выберите действие:",
        reply_markup=warehouse_quick_master_kb()
    )
    await callback.answer()


# Обработчики кнопок "нет товаров" и других служебных
@warehouse_router.callback_query(F.data == "warehouse_no_products")
async def no_products_handler(callback: CallbackQuery):
    """Обработчик для случая отсутствия товаров"""
    await callback.answer("❌ Нет доступных товаров", show_alert=True)


# Обработчик удален - не должен перехватывать все сообщения
# Все FSM состояния имеют свои специфичные обработчики