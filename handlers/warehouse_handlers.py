"""Обработчики для управления складом товаров"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
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
    warehouse_categories_compact_kb, warehouse_category_products_kb, warehouse_give_menu_kb,
    warehouse_main_categories_kb, warehouse_product_detail_kb, warehouse_product_action_complete_kb,
    warehouse_display_settings_kb, warehouse_error_recovery_kb, warehouse_categories_management_kb,
    warehouse_category_management_kb, warehouse_category_unified_management_kb,
    warehouse_category_action_complete_kb, warehouse_products_with_stock_kb,
    warehouse_out_of_stock_products_kb, warehouse_stock_summary_kb,
    warehouse_category_products_with_stock_kb, warehouse_quick_stock_select_kb
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
        # Получаем category_id для контекстного возврата
        category_id = data.get("category_id")
        await callback.message.edit_text(
            f"❌ <b>Ошибка валидации</b>\n\n{error_message}\n\n💡 Проверьте данные и попробуйте снова:",
            reply_markup=warehouse_error_recovery_kb(category_id, "add_product")
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
        # Ошибка добавления товара - предлагаем повторить попытку
        category_id = data.get("category_id")
        await callback.message.edit_text(
            "❌ <b>Ошибка при добавлении товара</b>\n\n"
            "Возможно, товар с таким названием уже существует или произошла ошибка базы данных.\n\n"
            "💡 Попробуйте еще раз или проверьте данные:",
            reply_markup=warehouse_error_recovery_kb(category_id, "add_product")
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
    
    # Возвращаемся в категорию товара с улучшенной навигацией
    category_id = updated_product.category_id if updated_product.category else 0
    
    await callback.message.edit_text(
        success_text,
        reply_markup=warehouse_category_action_complete_kb(category_id, action_type="give")
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
    
    # Генерируем детальное сообщение с форматом контента и примерами
    if product_type == ProductType.ACCOUNT.value:
        content_format = (
            "<b>👤 Массовое добавление аккаунтов</b>\n\n"
            "<b>📋 Поддерживаемые форматы:</b>\n"
            "• <code>email:password</code> (двоеточие)\n"
            "• <code>email|password</code> (вертикальная черта)\n"
            "• <code>email password</code> (пробел)\n"
            "• <code>email;password</code> (точка с запятой)\n"
            "• <code>email|password|optional|data</code> (с дополнительными данными)\n\n"
            "<b>💡 Примеры реальных аккаунтов:</b>\n"
            "<code>user@example.com:password123\n"
            "user2@example.com|mypassword456\n"
            "testuser@gmail.com | secret789 | backup@mail.com\n"
            "admin@service.com;adminpass2024;VIP\n"
            "premium@user.net strongpass extra_info</code>\n\n"
            "<b>✅ Гибкий формат данных:</b>\n"
            "• Основные: email и password (обязательно)\n"
            "• Дополнительные: backup email, статус, заметки\n"
            "• Поддержка любых разделителей: : | ; пробел TAB\n"
            "• Копирование из Excel/Sheets с сохранением структуры\n\n"
            "<b>✅ Автоматическая обработка:</b>\n"
            "• Проверка уникальности по email\n"
            "• Удаление пустых строк и лишних пробелов\n"
            "• Валидация формата email\n\n"
            "📝 <i>Каждая строка = 1 аккаунт</i>"
        )
    elif product_type == ProductType.KEY.value:
        content_format = (
            "<b>🔑 Массовое добавление ключей активации</b>\n\n"
            "<b>📋 Формат:</b> ключи активации, каждый с новой строки\n\n"
            "<b>💡 Примеры ключей:</b>\n"
            "<code>1234-5678-ABCD-EFGH\n"
            "9876-5432-WXYZ-MNOP\n"
            "ABCD-1234-EFGH-5678\n"
            "KEY1-KEY2-KEY3-KEY4\n"
            "PROD-2024-GAME-ACTI</code>\n\n"
            "<b>✅ Советы для массового импорта:</b>\n"
            "• Подойдут любые форматы ключей\n"
            "• Можно с дефисами или без\n"
            "• Система проверит уникальность\n"
            "• Пустые строки игнорируются\n\n"
            "📝 <i>Каждая строка = 1 ключ активации</i>"
        )
    else:  # PROMO
        content_format = (
            "<b>🎫 Массовое добавление промокодов</b>\n\n"
            "<b>📋 Формат:</b> промокоды, каждый с новой строки\n\n"
            "<b>💡 Примеры промокодов Perplexity:</b>\n"
            "<code>CODE-1-AAAA-BBBB\n"
            "CODE-2-CCCC-DDDD\n"
            "hH7LmWGWuEcUqoxKzGlPMqR2xF8vN3dL\n"
            "Rz8yxKPM0bt1O1mOx5UqA7wS9pE2nK4Y\n"
            "0yc4cKNhftkrzF7dmLNO6vP8qW1xR5uI</code>\n\n"
            "<b>💡 Другие форматы промокодов:</b>\n"
            "<code>SAVE20OFF\n"
            "DISCOUNT-2024-WINTER\n"
            "PRO_ACCESS_2024\n"
            "VIP-MEMBER-12345\n"
            "SPECIAL.OFFER.789</code>\n\n"
            "<b>✅ Советы для массового импорта:</b>\n"
            "• Копируйте промокоды из Excel/Google Sheets\n"
            "• Поддерживаются любые символы: дефисы, точки, подчеркивания\n"
            "• Автоматическая проверка уникальности\n"
            "• Пустые строки и лишние пробелы игнорируются\n"
            "• Длина промокода: от 5 до 64 символов\n\n"
            "📝 <i>Каждая строка = 1 промокод</i>"
        )
    
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
    
    # Формируем детальный отчет
    if report['successful'] > 0:
        total_value = len(products) * data["price"]
        
        success_text = f"✅ <b>Массовое добавление завершено!</b>\n\n"
        success_text += f"📦 <b>Результаты обработки:</b>\n"
        success_text += f"✅ Добавлено товаров: <b>{report['successful']}</b>\n"
        success_text += f"📋 Всего строк обработано: {report['total_lines']}\n\n"
        
        # Детальная статистика ошибок
        if report['empty_lines'] > 0:
            success_text += f"📄 Пустых строк: {report['empty_lines']}\n"
        if report['duplicates'] > 0:
            success_text += f"🔄 Дубликатов: {report['duplicates']}\n"
        if report['invalid_format'] > 0:
            success_text += f"❌ Неверный формат: {report['invalid_format']}\n"
        
        success_text += f"\n💰 <b>Финансы:</b>\n"
        success_text += f"💳 Общая стоимость: {total_value:.2f}₽\n"
        success_text += f"💵 Цена за единицу: {data['price']:.2f}₽\n\n"
        
        success_text += f"📂 <b>Итоговый остаток по категории:</b>\n"
        success_text += f"'{data['category_name']}': <b>{category_stock} шт.</b>\n\n"
        
        # Показываем конкретные ошибки если есть
        if report['errors']:
            success_text += f"⚠️ <b>Подробности ошибок ({len(report['errors'])}):</b>\n"
            # Показываем первые 3 ошибки для экономии места
            for error in report['errors'][:3]:
                success_text += f"• {error}\n"
            if len(report['errors']) > 3:
                success_text += f"• ... и еще {len(report['errors']) - 3} ошибок\n"
        
        # Добавляем информацию о типе товара для лучшего понимания
        type_names = {
            "account": "👤 Аккаунты",
            "key": "🔑 Ключи активации", 
            "promo": "🎫 Промокоды"
        }
        type_display = type_names.get(data["product_type"], data["product_type"])
        success_text += f"\n📋 <b>Тип товаров:</b> {type_display}\n"
        success_text += f"⏱ <b>Длительность:</b> {data['duration']}"
        
        # Возвращаемся в категорию с улучшенной навигацией
        category_id = data["category_id"]
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_category_action_complete_kb(category_id, action_type="add")
        )
        
        logger.info(f"WAREHOUSE: Mass added {len(products)} products by admin {callback.from_user.id}. "
                   f"Category: {data['category_name']}, Type: {data['product_type']}")
    else:
        # Если не добавлено ни одного товара - детальный разбор ошибок
        error_text = f"❌ <b>Товары не добавлены</b>\n\n"
        error_text += f"📋 <b>Статистика обработки:</b>\n"
        error_text += f"• Всего строк: {report['total_lines']}\n"
        error_text += f"• Успешно: {report['successful']}\n"
        error_text += f"• Ошибок: {len(report['errors'])}\n\n"
        
        # Разбиваем ошибки по типам
        if report['empty_lines'] > 0:
            error_text += f"📄 Пустых строк: {report['empty_lines']}\n"
        if report['duplicates'] > 0:
            error_text += f"🔄 Дубликатов: {report['duplicates']}\n"
        if report['invalid_format'] > 0:
            error_text += f"❌ Неверный формат: {report['invalid_format']}\n"
        
        error_text += f"\n<b>💡 Основные проблемы:</b>\n"
        for error in report['errors'][:8]:  # Показываем больше ошибок при полном провале
            error_text += f"• {error}\n"
        
        if len(report['errors']) > 8:
            error_text += f"• ... и еще {len(report['errors']) - 8} ошибок"
        
        # Возвращаемся в категорию с возможностью повторить попытку
        category_id = data["category_id"]
        
        # Создаем клавиатуру с повтором массового добавления
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data=f"warehouse_mass_add_to_category_{category_id}"),
            InlineKeyboardButton(text="📂 К категории", callback_data=f"warehouse_show_category_{category_id}_0")
        )
        builder.row(
            InlineKeyboardButton(text="➕ Добавить один товар", callback_data=f"warehouse_add_to_category_{category_id}"),
            InlineKeyboardButton(text="⚡ Быстрое добавление", callback_data=f"warehouse_quick_add_to_category_{category_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🏪 Главное меню склада", callback_data="warehouse_menu"),
            InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
        )
        
        await callback.message.edit_text(
            error_text,
            reply_markup=builder.as_markup()
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
    
    # Возвращаемся в категорию товара с улучшенной навигацией
    category_id = updated_product.category_id if updated_product.category else 0
    
    await callback.message.edit_text(
        success_text,
        reply_markup=warehouse_category_action_complete_kb(category_id, action_type="give")
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

# УДАЛЕН: Дублирующий обработчик warehouse_all_products_new
# Используется warehouse_all_products_callback на строке 2537


@warehouse_router.callback_query(F.data.startswith("warehouse_all_products_page_"))
async def warehouse_all_products_page_handler(callback: CallbackQuery, session: AsyncSession):
    """Обработчик пагинации для страницы всех товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Получаем номер страницы из callback_data
        page = int(callback.data.split("_")[-1])
        
        warehouse_service = WarehouseService(session)
        products = await warehouse_service.get_available_products()
        
        if not products:
            await callback.answer("❌ Товары не найдены", show_alert=True)
            return
        
        # Проверяем валидность страницы (должно совпадать с warehouse_all_products_kb)
        per_page = 5
        max_page = (len(products) - 1) // per_page
        if page < 0 or page > max_page:
            await callback.answer("❌ Страница не найдена", show_alert=True)
            return
        
        await callback.message.edit_reply_markup(
            reply_markup=warehouse_all_products_kb(products, page)
        )
        await callback.answer()
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error in warehouse_all_products_page_handler: {e}")
        await callback.answer("❌ Ошибка обработки страницы", show_alert=True)


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


# ========== ОБРАБОТКА НЕДЕЙСТВИТЕЛЬНЫХ CALLBACK'ОВ ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_category_products_"))
async def warehouse_category_products_redirect(callback: CallbackQuery, session: AsyncSession):
    """Перенаправление со старого callback на новый для избежания зависших меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
        
    try:
        # Парсим старый callback и перенаправляем на новый
        parts = callback.data.split("_")
        category_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 0
        
        # Перенаправляем на новый обработчик
        callback.data = f"warehouse_show_category_{category_id}_{page}"
        await warehouse_show_category_handler(callback, session)
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error redirecting old callback: {e}")
        await callback.answer("❌ Ошибка обработки. Обновляем меню...", show_alert=True)
        
        # Возвращаемся к главному меню склада
        warehouse_service = WarehouseService(session)
        category_stats = await warehouse_service.get_category_stats()
        
        await callback.message.edit_text(
            "📦 <b>Меню обновлено</b>\n\nВыберите категорию для просмотра товаров:",
            reply_markup=warehouse_categories_compact_kb(category_stats)
        )


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
    """Показать подтверждение редактирования товара с улучшенным отображением"""
    data = await state.get_data()
    product_id = data.get("product_id")
    
    warehouse_service = WarehouseService(session)
    product = await warehouse_service.get_product_with_category(product_id)
    
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    # Формируем список изменений с красивым форматированием
    changes = []
    has_changes = False
    
    if "new_name" in data and data["new_name"] != product.name:
        changes.append(f"🏷 <b>Название:</b>\n  ▫️ <s>{product.name}</s>\n  ▪️ <b>{data['new_name']}</b>")
        has_changes = True
    
    if "new_type" in data and data["new_type"] != product.product_type:
        old_type_display = WarehouseMessages.get_product_type_display(product.product_type)
        new_type_display = WarehouseMessages.get_product_type_display(data["new_type"])
        changes.append(f"📦 <b>Тип:</b>\n  ▫️ <s>{old_type_display}</s>\n  ▪️ <b>{new_type_display}</b>")
        has_changes = True
    
    if "new_duration" in data and data["new_duration"] != product.duration:
        old_duration = product.duration or "Не указана"
        changes.append(f"⏱ <b>Длительность:</b>\n  ▫️ <s>{old_duration}</s>\n  ▪️ <b>{data['new_duration']}</b>")
        has_changes = True
    
    if "new_price" in data and data["new_price"] != product.price:
        changes.append(f"💰 <b>Цена:</b>\n  ▫️ <s>{product.price}₽</s>\n  ▪️ <b>{data['new_price']}₽</b>")
        has_changes = True
    
    if "new_content" in data and data["new_content"] != product.digital_content:
        old_preview = WarehouseMessages.get_content_preview(product.digital_content or "", product.product_type)
        new_preview = WarehouseMessages.get_content_preview(data["new_content"], product.product_type)
        changes.append(f"📋 <b>Содержимое:</b>\n  ▫️ <s>{old_preview}</s>\n  ▪️ <b>{new_preview}</b>")
        has_changes = True
    
    if not has_changes:
        await message.answer(
            "❌ <b>Изменения не обнаружены</b>\n\nВы не внесли никаких изменений в товар.",
            reply_markup=back_to_warehouse_kb()
        )
        await state.clear()
        return
    
    changes_text = "\n\n".join(changes)
    
    await state.set_state(WarehouseEditProductStates.waiting_for_confirmation)
    
    confirmation_text = (
        f"📝 <b>Подтверждение редактирования</b>\n\n"
        f"🛍 <b>Товар:</b> {product.name}\n"
        f"🆔 <b>ID:</b> #{product.id}\n\n"
        f"<b>📋 Изменения:</b>\n\n"
        f"{changes_text}\n\n"
        f"❓ <b>Сохранить изменения?</b>"
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
        # Показываем детальное успешное обновление
        stock_display = "∞" if updated_product.is_unlimited else str(updated_product.stock_quantity)
        product_type_display = WarehouseMessages.get_product_type_display(updated_product.product_type)
        content_preview = WarehouseMessages.get_content_preview(updated_product.digital_content or "", updated_product.product_type)
        
        success_text = (
            f"✅ <b>Товар успешно обновлен!</b>\n\n"
            f"🆔 <b>ID:</b> #{updated_product.id}\n"
            f"🏷 <b>Название:</b> {updated_product.name}\n"
            f"📂 <b>Категория:</b> {updated_product.category.name if updated_product.category else 'Неизвестная'}\n"
            f"📦 <b>Тип:</b> {product_type_display}\n"
            f"⏱ <b>Длительность:</b> {updated_product.duration or 'Не указана'}\n"
            f"💰 <b>Цена:</b> {updated_product.price:.2f}₽\n"
            f"📊 <b>Остаток:</b> {stock_display} шт.\n"
            f"📋 <b>Содержимое:</b> {content_preview}\n\n"
            f"🔄 <b>Товар обновлен в каталоге и готов к продаже!</b>"
        )
        
        # Возвращаемся в категорию товара с улучшенной навигацией
        category_id = updated_product.category_id if updated_product.category else 0
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_category_action_complete_kb(category_id, action_type="edit")
        )
        
        logger.info(f"WAREHOUSE: Product {product_id} edited by admin {callback.from_user.id}")
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка при обновлении товара</b>\n\n Попробуйте еще раз или обратитесь к техническому специалисту.",
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
    
    try:
        # Парсим product_id
        product_id = int(callback.data.split("_")[-1])
        logger.info(f"Admin {callback.from_user.id} requested deletion of product {product_id}")
        
        warehouse_service = WarehouseService(session)
        
        product = await warehouse_service.get_product_with_category(product_id)
        if not product:
            # Товар не найден - возвращаемся к актуальному списку товаров
            await callback.answer("❌ Товар не найден. Обновляем список...", show_alert=True)
            
            # Возвращаемся к списку всех категорий
            category_stats = await warehouse_service.get_category_stats()
            await callback.message.edit_text(
                "❌ <b>Товар не найден</b>\n\n"
                "Возможно, товар уже был удален.\n"
                "Список товаров обновлен.",
                reply_markup=warehouse_categories_compact_kb(category_stats)
            )
            return
        
        stock_display = "∞" if product.is_unlimited else str(product.stock_quantity)
        
        confirmation_text = (
            f"⚠️ <b>Подтверждение удаления товара</b>\n\n"
            f"🆔 <b>ID:</b> #{product.id}\n"
            f"📦 <b>Название:</b> {product.name}\n"
            f"📂 <b>Категория:</b> {product.category.name if product.category else 'Неизвестная'}\n"
            f"💰 <b>Цена:</b> {product.price:.2f}₽\n"
            f"📊 <b>Остаток:</b> {stock_display} шт.\n\n"
            f"❓ <b>Вы уверены, что хотите удалить этот товар?</b>\n\n"
            f"⚠️ <i>Товар будет перемещен в архив и станет недоступен для покупки.</i>"
        )
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        
        # Сохраняем category_id для возврата к списку товаров категории
        category_id = product.category_id if product.category else 0
        
        builder.row(
            InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"warehouse_confirm_delete_{product_id}_{category_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"warehouse_show_category_{category_id}_0" if category_id else "warehouse_all_products")
        )
        
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in delete_product_confirm: {e}")
        await callback.answer("❌ Произошла ошибка при подготовке к удалению", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_confirm_delete_"))
async def confirm_delete_product(callback: CallbackQuery, session: AsyncSession):
    """Окончательное удаление товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Парсим callback_data: warehouse_confirm_delete_{product_id}_{category_id}
        parts = callback.data.split("_")
        product_id = int(parts[-2])  # предпоследний элемент - product_id
        category_id = int(parts[-1])  # последний элемент - category_id
        
        logger.info(f"Admin {callback.from_user.id} confirmed deletion of product {product_id}")
        
        warehouse_service = WarehouseService(session)
        
        # Получаем товар перед удалением
        product = await warehouse_service.get_product_with_category(product_id)
        if not product:
            # Товар не найден - возвращаемся к актуальному списку товаров
            await callback.answer("❌ Товар не найден. Обновляем список...", show_alert=True)
            
            # Пытаемся вернуться к категории, если знаем category_id
            if category_id:
                callback.data = f"warehouse_show_category_{category_id}_0"
                await warehouse_show_category_handler(callback, session)
            else:
                # Возвращаемся к списку всех категорий
                category_stats = await warehouse_service.get_category_stats()
                await callback.message.edit_text(
                    "❌ <b>Товар не найден</b>\n\n"
                    "Возможно, товар уже был удален.\n"
                    "Список товаров обновлен.",
                    reply_markup=warehouse_categories_compact_kb(category_stats)
                )
            return
        
        # Сохраняем информацию о товаре для сообщения
        product_name = product.name
        product_price = product.price
        category_name = product.category.name if product.category else "Неизвестная"
        
        # Помечаем товар как неактивный (мягкое удаление)
        product.is_active = False
        
        # Логируем удаление
        await warehouse_service._log_warehouse_action(
            product_id=product_id,
            admin_id=callback.from_user.id,
            admin_username=callback.from_user.username,
            action="delete_product",
            quantity=0,
            description=f"Удален товар: {product_name} из категории {category_name}"
        )
        
        await session.commit()
        logger.info(f"WAREHOUSE: Product {product_id} successfully deleted by admin {callback.from_user.id}")
        
        success_text = (
            f"✅ <b>Товар успешно удален!</b>\n\n"
            f"📦 <b>Название:</b> {product_name}\n"
            f"🆔 <b>ID:</b> #{product_id}\n"
            f"📂 <b>Категория:</b> {category_name}\n"
            f"💰 <b>Цена:</b> {product_price:.2f}₽\n\n"
            f"🗂 Товар перемещен в архив и больше не доступен для заказа.\n\n"
            f"💡 <i>Что делать дальше?</i>"
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=warehouse_category_action_complete_kb(category_id, action_type="delete")
        )
        
        # Отправляем уведомление об успехе
        await callback.answer("✅ Товар успешно удален!", show_alert=True)
        
    except ValueError as e:
        logger.error(f"Error parsing callback_data in confirm_delete_product: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
        await callback.message.edit_text(
            "❌ <b>Ошибка обработки данных</b>\n\nПопробуйте еще раз.",
            reply_markup=back_to_warehouse_kb()
        )
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        await session.rollback()
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при удалении товара</b>\n\n"
            f"Произошла ошибка: {str(e)}\n\n"
            f"Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=back_to_warehouse_kb()
        )
        await callback.answer("❌ Ошибка при удалении товара", show_alert=True)
    
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
    """Показать улучшенное меню способов добавления товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📥 <b>Добавить/Импортировать товары</b>\n\n"
        "💡 <b>Выберите удобный способ:</b>\n\n"
        "➕ <b>Один товар</b> - пошаговое добавление\n"
        "📦 <b>Массово</b> - много товаров одного типа\n"
        "⚡ <b>Быстрое</b> - все данные одним сообщением\n"
        "📄 <b>Импорт</b> - загрузка из файла\n"
        "🔄 <b>Дублировать</b> - копировать существующий товар",
        reply_markup=warehouse_add_menu_kb()
    )
    await callback.answer()


@warehouse_router.callback_query(F.data == "warehouse_give_menu")
async def warehouse_give_menu_callback(callback: CallbackQuery):
    """Показать объединенное меню выдачи товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎯 <b>Выдать товары</b>\n\n"
        "💡 <b>Выберите способ выдачи:</b>\n\n"
        "⚡ <b>Быстрая выдача</b> - поиск товара + пользователь\n"
        "🎯 <b>Выбрать товар</b> - из списка доступных\n"
        "🔍 <b>Поиск товара</b> - найти по названию/ID\n"
        "👥 <b>Найти пользователя</b> - поиск получателя\n"
        "📦 <b>Массовая выдача</b> - выдать много товаров",
        reply_markup=warehouse_give_menu_kb()
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


# ========== БЫСТРЫЕ ДЕЙСТВИЯ ДЛЯ КАТЕГОРИЙ ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_add_to_category_"))
async def add_to_category_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Добавить товар в конкретную категорию (быстрый путь)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
        
    category_id = int(callback.data.split("_")[-1])
    
    # Проверяем, что категория существует
    warehouse_service = WarehouseService(session)
    category = await warehouse_service.get_category_by_id(category_id)
    
    if not category:
        await callback.message.edit_text(
            "❌ Категория не найдена",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Устанавливаем состояние и сохраняем категорию
    await state.update_data(category_id=category_id)
    await state.set_state(WarehouseAddProductStates.waiting_for_name)
    
    await callback.message.edit_text(
        f"🎯 <b>Быстрое добавление в категорию</b>\n\n"
        f"📂 <b>Категория:</b> {category.name}\n\n"
        f"🏷 <b>Шаг 1/5:</b> Введите название товара:\n\n"
        f"💡 <i>Например: Курсор про 1 месяц</i>",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_mass_add_to_category_"))
async def mass_add_to_category_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Массовое добавление в конкретную категорию (быстрый путь)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
        
    category_id = int(callback.data.split("_")[-1])
    
    # Проверяем, что категория существует
    warehouse_service = WarehouseService(session)
    category = await warehouse_service.get_category_by_id(category_id)
    
    if not category:
        await callback.message.edit_text(
            "❌ Категория не найдена",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Устанавливаем состояние и сохраняем категорию
    await state.update_data(category_id=category_id)
    await state.set_state(WarehouseMassAddStates.waiting_for_name)
    
    await callback.message.edit_text(
        f"📦 <b>Массовое добавление в категорию</b>\n\n"
        f"📂 <b>Категория:</b> {category.name}\n\n"
        f"🏷 <b>Шаг 1/5:</b> Введите базовое название товара:\n\n"
        f"💡 <i>Например: Курсор про (товары будут пронумерованы автоматически)</i>",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_quick_add_to_category_"))
async def quick_add_to_category_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Быстрое добавление в конкретную категорию"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
        
    category_id = int(callback.data.split("_")[-1])
    
    # Проверяем, что категория существует
    warehouse_service = WarehouseService(session)
    category = await warehouse_service.get_category_by_id(category_id)
    
    if not category:
        await callback.message.edit_text(
            "❌ Категория не найдена",
            reply_markup=back_to_warehouse_kb()
        )
        return
    
    # Устанавливаем состояние и сохраняем категорию
    await state.update_data(category_id=category_id)
    await state.set_state(WarehouseQuickAddStates.waiting_for_all_data)
    
    await callback.message.edit_text(
        f"⚡ <b>Быстрое добавление в категорию</b>\n\n"
        f"📂 <b>Категория:</b> {category.name}\n\n"
        f"📝 <b>Введите данные товара одним сообщением:</b>\n\n"
        f"<b>Формат:</b>\n"
        f"<code>Название товара\n"
        f"Тип: аккаунт/ключ/промокод\n"
        f"Длительность: 1 месяц\n"
        f"Цена: 299\n"
        f"Контент: логин:пароль</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>Perplexity pro\n"
        f"Тип: Промокод\n"
        f"Длительность: 1 год\n"
        f"Цена: 549\n"
        f"Контент: SAVE20OFF:password123</code>",
        reply_markup=cancel_kb()
    )
    await callback.answer()


# ========== ЗАГЛУШКИ ДЛЯ НОВЫХ ФУНКЦИЙ ==========

@warehouse_router.callback_query(F.data == "warehouse_import_file")
async def warehouse_import_file_callback(callback: CallbackQuery):
    """Заглушка для импорта из файла"""
    await callback.answer("🚧 Функция в разработке. Скоро будет доступна!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_duplicate_product") 
async def warehouse_duplicate_product_callback(callback: CallbackQuery):
    """Заглушка для дублирования товара"""
    await callback.answer("🚧 Функция в разработке. Скоро будет доступна!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_search_product")
async def warehouse_search_product_callback(callback: CallbackQuery):
    """Заглушка для поиска товара"""
    await callback.answer("🚧 Используйте 'Быстрая выдача' для поиска товаров", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_find_user")
async def warehouse_find_user_callback(callback: CallbackQuery):
    """Заглушка для поиска пользователя"""
    await callback.answer("🚧 Используйте 'Быстрая выдача' для поиска пользователей", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_mass_give")
async def warehouse_mass_give_callback(callback: CallbackQuery):
    """Заглушка для массовой выдачи"""
    await callback.answer("🚧 Функция в разработке. Скоро будет доступна!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_management")
async def warehouse_management_callback(callback: CallbackQuery):
    """Заглушка для управления складом"""
    await callback.answer("🚧 Дополнительные функции управления в разработке!", show_alert=True)


# Обработчики кнопок "нет товаров" и других служебных
@warehouse_router.callback_query(F.data == "warehouse_no_products")
async def no_products_handler(callback: CallbackQuery):
    """Обработчик для случая отсутствия товаров"""
    await callback.answer("❌ Нет доступных товаров", show_alert=True)


# ========== НОВАЯ НАВИГАЦИЯ ПО КАТЕГОРИЯМ ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_show_category_"))
async def warehouse_show_category_handler(callback: CallbackQuery, session: AsyncSession):
    """Показать товары в выбранной категории - компактное отображение"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Парсим callback data: warehouse_show_category_{category_id} или warehouse_show_category_{category_id}_{page}
        parts = callback.data.split("_")
        category_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 0
        
        warehouse_service = WarehouseService(session)
        
        # Получаем категорию
        category = await warehouse_service.get_category_by_id(category_id)
        if not category:
            await callback.message.edit_text(
                "❌ <b>Категория не найдена</b>\n\nВозможно, категория была удалена.",
                reply_markup=back_to_warehouse_kb()
            )
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Получаем товары в категории
        products = await warehouse_service.get_products_by_category(category_id)
        
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
        
        per_page = 10  # Стандартная пагинация - 10 товаров на страницу
        total_pages = (len(products) + per_page - 1) // per_page if products else 1
        
        # Вычисляем границы для текущей страницы
        start = page * per_page
        end = min(start + per_page, len(products))
        current_page_count = end - start if products else 0
        
        text = (
            f"📂 <b>Категория: {category.name}</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего товаров: {len(products)}\n"
            f"• Доступно: {available_count}\n"
            f"• Остаток: {stock_display} шт.\n\n"
        )
        
        if not products:
            text += (
                f"❌ <b>Товары в категории не найдены</b>\n\n"
                f"💡 Добавьте первые товары в эту категорию:"
            )
        else:
            if total_pages > 1:
                text += f"📄 <b>Страница {page + 1} из {total_pages}</b>\n"
                text += f"📋 Показано товаров: {current_page_count} из {len(products)}\n\n"
            else:
                text += f"📋 <b>Показано все товары:</b> {len(products)}\n\n"
            
            text += "🛍 <b>Выберите товар для управления:</b>\n"
            if len(products) > 10:
                text += "💡 <i>Используйте кнопки ⬅️➡️ для навигации по страницам</i>"
        
        await callback.message.edit_text(
            text,
            reply_markup=warehouse_category_products_kb(products, category_id, category.name, page, per_page)
        )
        await callback.answer()
        
    except ValueError as e:
        logger.error(f"Error parsing callback_data in warehouse_show_category_handler: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
    except Exception as e:
        logger.error(f"Error in warehouse_show_category_handler: {e}")
        await callback.answer("❌ Произошла ошибка при загрузке категории", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_product_detail_"))
async def warehouse_product_detail_handler(callback: CallbackQuery, session: AsyncSession):
    """Показать детальную информацию о товаре с действиями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Парсим callback data: warehouse_product_detail_{product_id}_{category_id}_{page}
        logger.info(f"Processing callback data: {callback.data}")
        parts = callback.data.split("_")
        logger.info(f"Callback parts: {parts}")
        
        if len(parts) < 5:
            raise ValueError(f"Invalid callback format: expected at least 5 parts, got {len(parts)}")
        
        # Проверяем, что это действительно числа
        try:
            product_id = int(parts[3])
            category_id = int(parts[4])
            page = int(parts[5]) if len(parts) > 5 else 0
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid numeric values in callback: {parts[3:]}, error: {e}")
        
        # Проверяем валидность значений
        if product_id <= 0:
            raise ValueError(f"Invalid product_id: {product_id}")
        if category_id <= 0:
            raise ValueError(f"Invalid category_id: {category_id}")
        if page < 0:
            raise ValueError(f"Invalid page: {page}")
        
        logger.info(f"Parsed: product_id={product_id}, category_id={category_id}, page={page}")
        
        # Проверяем сессию базы данных
        if not session:
            raise Exception("Database session is None")
        
        warehouse_service = WarehouseService(session)
        
        # Получаем товар с категорией
        logger.info(f"Fetching product with ID: {product_id}")
        try:
            product = await warehouse_service.get_product_with_category(product_id)
        except Exception as db_error:
            logger.error(f"Database error while fetching product {product_id}: {db_error}")
            raise Exception(f"Database error: {db_error}")
        
        if not product:
            logger.warning(f"Product not found: product_id={product_id}")
            await callback.message.edit_text(
                f"❌ <b>Товар не найден</b>\n\n"
                f"Товар с ID #{product_id} не существует или был удален.\n"
                f"Возможно, товар был удален другим администратором.",
                reply_markup=back_to_warehouse_kb()
            )
            await callback.answer("❌ Товар не найден", show_alert=True)
            return
        
        logger.info(f"Product found: {product.name} (ID: {product.id})")
        
        # Получаем тип товара
        product_type_display = {
            'account': '👤 Аккаунт',
            'key': '🔑 Ключ активации', 
            'promo': '🎫 Промокод'
        }.get(product.product_type, '❓ Неизвестный тип')
        
        # Показываем остатки
        if product.is_unlimited:
            stock_display = "∞ (безлимитный)"
            status_icon = "♾️"
        elif product.stock_quantity > 0:
            stock_display = f"{product.stock_quantity} шт."
            if product.stock_quantity > 10:
                status_icon = "🟢"
            elif product.stock_quantity > 5:
                status_icon = "🟡"
            else:
                status_icon = "⚠️"
        else:
            stock_display = "0 шт. (закончился)"
            status_icon = "🔴"
        
        # Формируем превью контента
        if product.digital_content:
            if len(product.digital_content) > 100:
                content_preview = product.digital_content[:100] + "..."
            else:
                content_preview = product.digital_content
        else:
            content_preview = "Не указано"
        
        text = (
            f"{status_icon} <b>Детали товара</b>\n\n"
            f"🆔 <b>ID:</b> #{product.id}\n"
            f"🏷 <b>Название:</b> {product.name}\n"
            f"📂 <b>Категория:</b> {product.category.name if product.category else 'Неизвестная'}\n"
            f"📦 <b>Тип:</b> {product_type_display}\n"
            f"⏱ <b>Длительность:</b> {product.duration or 'Не указана'}\n"
            f"💰 <b>Цена:</b> {product.price:.2f}₽\n"
            f"📊 <b>Остаток:</b> {stock_display}\n\n"
            f"📋 <b>Содержимое:</b>\n"
            f"<code>{content_preview}</code>\n\n"
            f"💡 <b>Выберите действие:</b>"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=warehouse_product_detail_kb(product_id, category_id, page)
        )
        await callback.answer()
        
    except ValueError as e:
        logger.error(f"Error parsing callback_data in warehouse_product_detail_handler: {e}")
        logger.error(f"Callback data: {callback.data}")
        await callback.message.edit_text(
            "❌ <b>Ошибка обработки данных</b>\n\n"
            "Неверный формат данных товара.\n"
            "Попробуйте выбрать товар снова.",
            reply_markup=back_to_warehouse_kb()
        )
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
    except Exception as e:
        logger.error(f"Error in warehouse_product_detail_handler: {e}")
        logger.error(f"Callback data: {callback.data}")
        logger.error(f"User ID: {callback.from_user.id}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        await callback.message.edit_text(
            "❌ <b>Ошибка при загрузке товара</b>\n\n"
            "Произошла техническая ошибка.\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=back_to_warehouse_kb()
        )
        await callback.answer("❌ Произошла ошибка при загрузке товара", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_duplicate_"))
async def warehouse_duplicate_product_handler(callback: CallbackQuery):
    """Заглушка для дублирования товара"""
    await callback.answer("🚧 Функция дублирования товаров в разработке!", show_alert=True)


# ========== НОВАЯ ИЕРАРХИЧЕСКАЯ СТРУКТУРА ==========

@warehouse_router.callback_query(F.data == "warehouse_all_products")
async def warehouse_all_products_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать все товары по категориям - классическая иерархия"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    warehouse_service = WarehouseService(session)
    category_stats = await warehouse_service.get_category_stats()
    
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
    
    if not category_stats:
        text = (
            f"📦 <b>Все товары</b>\n\n"
            f"❌ Категории не найдены.\n\n"
            f"💡 Создайте первую категорию для добавления товаров."
        )
    else:
        text = (
            f"📦 <b>Все товары по категориям</b>\n\n"
            f"📊 <b>Общая статистика:</b>\n"
            f"• Категорий: {len(category_stats)}\n"
            f"• Товаров: {total_products}\n"
            f"• Остаток: {stock_display} шт.\n\n"
            f"📂 <b>Выберите категорию для просмотра товаров:</b>"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=warehouse_categories_compact_kb(category_stats)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data == "warehouse_display_settings")
async def warehouse_display_settings_callback(callback: CallbackQuery):
    """Показать настройки отображения товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    text = (
        f"⚙️ <b>Настройки отображения товаров</b>\n\n"
        f"🔧 <b>Настройте внешний вид склада под ваши потребности:</b>\n\n"
        f"📋 <b>Плоское отображение</b> - все товары в одном списке\n"
        f"🗂 <b>Иерархическое</b> - товары по категориям (текущий режим)\n\n"
        f"📄 <b>Пагинация</b> - количество товаров на странице\n"
        f"🔤 <b>Сортировка</b> - порядок отображения товаров\n\n"
        f"💡 <i>Настройки сохраняются автоматически</i>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=warehouse_display_settings_kb()
    )
    await callback.answer()


# ========== ЗАГЛУШКИ ДЛЯ НАСТРОЕК ОТОБРАЖЕНИЯ ==========

@warehouse_router.callback_query(F.data == "warehouse_set_display_flat")
async def set_display_flat_callback(callback: CallbackQuery):
    """Установить плоское отображение"""
    await callback.answer("🚧 Плоское отображение будет добавлено в следующих версиях!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_set_display_hierarchy")
async def set_display_hierarchy_callback(callback: CallbackQuery):
    """Установить иерархическое отображение"""
    await callback.answer("✅ Иерархическое отображение уже активно!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_set_per_page_5")
async def set_per_page_5_callback(callback: CallbackQuery):
    """Установить 5 товаров на странице"""
    await callback.answer("🚧 Настройки пагинации в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_set_per_page_10")
async def set_per_page_10_callback(callback: CallbackQuery):
    """Установить 10 товаров на странице"""
    await callback.answer("🚧 Настройки пагинации в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_set_sort_name")
async def set_sort_name_callback(callback: CallbackQuery):
    """Сортировать по алфавиту"""
    await callback.answer("🚧 Настройки сортировки в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_set_sort_stock")
async def set_sort_stock_callback(callback: CallbackQuery):
    """Сортировать по остатку"""
    await callback.answer("🚧 Настройки сортировки в разработке!", show_alert=True)


# ========== ЗАГЛУШКИ ДЛЯ НОВЫХ ФУНКЦИЙ ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_edit_category_"))
async def edit_category_callback(callback: CallbackQuery):
    """Заглушка для редактирования категории"""
    await callback.answer("🚧 Функция редактирования категорий в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_mass_delete_category_"))
async def mass_delete_category_callback(callback: CallbackQuery):
    """Заглушка для массового удаления товаров категории"""
    category_id = callback.data.split("_")[-1]
    await callback.answer("🚧 Функция массового удаления товаров в разработке!", show_alert=True)


# ========== МЕНЮ УПРАВЛЕНИЯ КАТЕГОРИЯМИ ==========

@warehouse_router.callback_query(F.data == "warehouse_categories_menu")
async def warehouse_categories_menu_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать меню управления категориями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    warehouse_service = WarehouseService(session)
    categories = await warehouse_service.get_categories()
    
    # Считаем общую статистику
    total_categories = len(categories)
    total_products = 0
    empty_categories = 0
    
    # Считаем товары по всем категориям и создаем словарь для клавиатуры
    category_products_count = {}
    for category in categories:
        category_products = await warehouse_service.get_products_by_category(category.id)
        category_products_count[category.id] = len(category_products) if category_products else 0
        if category_products:
            total_products += len(category_products)
        else:
            empty_categories += 1
    
    if not categories:
        text = (
            f"📂 <b>Управление категориями</b>\n\n"
            f"❌ Категории не найдены.\n\n"
            f"💡 Создайте первую категорию для организации товаров."
        )
    else:
        text = (
            f"📂 <b>Управление категориями</b>\n\n"
            f"📊 <b>Общая статистика:</b>\n"
            f"• Категорий: <b>{total_categories}</b>\n"
            f"• Товаров: <b>{total_products}</b>\n"
            f"• Пустых категорий: <b>{empty_categories}</b>\n\n"
            f"💡 <b>Выберите категорию для управления:</b>"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=warehouse_categories_management_kb(categories, category_products_count)
    )
    await callback.answer()


@warehouse_router.callback_query(F.data.startswith("warehouse_manage_category_"))
async def warehouse_manage_category_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать меню управления конкретной категорией"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        category_id = int(callback.data.split("_")[-1])
        warehouse_service = WarehouseService(session)
        
        # Получаем категорию
        category = await warehouse_service.get_category_by_id(category_id)
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Получаем товары в категории
        products = await warehouse_service.get_products_by_category(category_id)
        
        # Считаем статистику
        total_products = len(products)
        available_products = sum(1 for p in products if p.is_unlimited or p.stock_quantity > 0)
        total_stock = sum(p.stock_quantity for p in products if not p.is_unlimited)
        unlimited_count = sum(1 for p in products if p.is_unlimited)
        
        # Формируем отображение остатков
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
        
        text = (
            f"📂 <b>Управление категорией</b>\n"
            f"📁 <b>Название:</b> {category.name}\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего товаров: <b>{total_products}</b>\n"
            f"• Доступно: <b>{available_products}</b>\n"
            f"• Остаток: <b>{stock_display}</b> шт.\n\n"
        )
        
        if category.description:
            text += f"📝 <b>Описание:</b>\n{category.description}\n\n"
        
        if category.manual_url:
            text += f"🔗 <b>Инструкция:</b> {category.manual_url}\n\n"
        
        text += f"💡 <b>Выберите действие:</b>"
        
        # Перенаправляем на единое управление категорией
        await warehouse_category_unified_management_handler(callback, session)
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error in warehouse_manage_category_callback: {e}")
        await callback.answer("❌ Ошибка обработки категории", show_alert=True)


# ========== ЕДИНОЕ УПРАВЛЕНИЕ КАТЕГОРИЕЙ ==========

@warehouse_router.callback_query(F.data.startswith("warehouse_category_management_"))
async def warehouse_category_unified_management_handler(callback: CallbackQuery, session: AsyncSession):
    """Единое меню управления категорией - товары + действия + статистика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Парсим callback: warehouse_category_management_{category_id}_{page}
        parts = callback.data.split("_")
        category_id = int(parts[3])
        page = int(parts[4]) if len(parts) > 4 else 0
        
        warehouse_service = WarehouseService(session)
        
        # Получаем категорию
        category = await warehouse_service.get_category_by_id(category_id)
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Получаем товары в категории
        products = await warehouse_service.get_products_by_category(category_id)
        
        # Считаем статистику
        total_products = len(products)
        available_products = sum(1 for p in products if p.is_unlimited or p.stock_quantity > 0)
        total_stock = sum(p.stock_quantity for p in products if not p.is_unlimited)
        unlimited_count = sum(1 for p in products if p.is_unlimited)
        
        # Формируем отображение остатков
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
        
        # Формируем текст сообщения
        per_page = 10
        total_pages = (len(products) + per_page - 1) // per_page if products else 1
        start = page * per_page
        end = min(start + per_page, len(products))
        
        text = (
            f"🎛 <b>Управление категорией: {category.name}</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего товаров: <b>{total_products}</b>\n"
            f"• Доступно: <b>{available_products}</b>\n"
            f"• Остаток: <b>{stock_display}</b> шт.\n"
        )
        
        if category.description:
            text += f"• Описание: {category.description}\n"
        
        if products:
            if total_pages > 1:
                text += f"\n📄 <b>Страница {page + 1} из {total_pages}</b>\n"
                text += f"📋 Показано: {end - start} из {total_products} товаров\n\n"
            else:
                text += f"\n📋 <b>Товары в категории:</b>\n"
            
            text += "💡 <i>Нажмите на товар для подробных действий</i>"
        else:
            text += "\n❌ <b>Товары отсутствуют</b>\n"
            text += "💡 Добавьте первые товары в категорию"
        
        await callback.message.edit_text(
            text,
            reply_markup=warehouse_category_unified_management_kb(
                products, category_id, category.name, page, per_page
            )
        )
        await callback.answer()
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback in warehouse_category_unified_management_handler: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
    except Exception as e:
        logger.error(f"Error in warehouse_category_unified_management_handler: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ========== ЗАГЛУШКИ ДЛЯ СТАТИСТИКИ И МАССОВЫХ ОПЕРАЦИЙ ==========

@warehouse_router.callback_query(F.data == "warehouse_categories_stats")
async def warehouse_categories_stats_callback(callback: CallbackQuery):
    """Заглушка для статистики категорий"""
    await callback.answer("🚧 Детальная статистика категорий в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_categories_bulk")
async def warehouse_categories_bulk_callback(callback: CallbackQuery):
    """Заглушка для массовых операций с категориями"""
    await callback.answer("🚧 Массовые операции с категориями в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_category_stats_"))
async def warehouse_category_stats_callback(callback: CallbackQuery):
    """Заглушка для статистики конкретной категории"""
    await callback.answer("🚧 Статистика категории в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_delete_category_"))
async def warehouse_delete_category_callback(callback: CallbackQuery):
    """Заглушка для удаления категории"""
    await callback.answer("🚧 Удаление категорий в разработке!", show_alert=True)


# ========== ЗАГЛУШКА ДЛЯ НЕАКТИВНЫХ КНОПОК ==========

@warehouse_router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Заглушка для неактивных кнопок (разделители)"""
    await callback.answer()


# Обработчик удален - не должен перехватывать все сообщения
# Все FSM состояния имеют свои специфичные обработчики

# ========== ОБРАБОТЧИКИ ДЛЯ РАБОТЫ С ОСТАТКАМИ ==========

@warehouse_router.callback_query(F.data == "warehouse_products_with_stock")
async def warehouse_products_with_stock_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать товары с остатками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        warehouse_service = WarehouseService(session)
        products = await warehouse_service.get_all_products()
        
        if not products:
            await callback.message.edit_text(
                "❌ Товары не найдены",
                reply_markup=back_to_warehouse_kb()
            )
            await callback.answer()
            return
        
        # Используем новую клавиатуру для товаров с остатками
        from keyboards.warehouse_keyboards import warehouse_products_with_stock_kb
        
        await callback.message.edit_text(
            "🟢 <b>Товары с остатками</b>\n\n"
            "Выберите товар для просмотра или выдачи:",
            reply_markup=warehouse_products_with_stock_kb(products, page=0)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_products_with_stock_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_products_stock_page_"))
async def warehouse_products_stock_page_callback(callback: CallbackQuery, session: AsyncSession):
    """Пагинация для товаров с остатками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        page = int(callback.data.split("_")[-1])
        warehouse_service = WarehouseService(session)
        products = await warehouse_service.get_all_products()
        
        from keyboards.warehouse_keyboards import warehouse_products_with_stock_kb
        
        await callback.message.edit_text(
            "🟢 <b>Товары с остатками</b>\n\n"
            "Выберите товар для просмотра или выдачи:",
            reply_markup=warehouse_products_with_stock_kb(products, page=page)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_products_stock_page_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_show_out_of_stock")
async def warehouse_show_out_of_stock_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать товары без остатков"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        warehouse_service = WarehouseService(session)
        products = await warehouse_service.get_all_products()
        
        if not products:
            await callback.message.edit_text(
                "❌ Товары не найдены",
                reply_markup=back_to_warehouse_kb()
            )
            await callback.answer()
            return
        
        # Используем клавиатуру для товаров без остатков
        from keyboards.warehouse_keyboards import warehouse_out_of_stock_products_kb
        
        await callback.message.edit_text(
            "🔴 <b>Товары без остатков</b>\n\n"
            "Эти товары закончились и требуют пополнения:",
            reply_markup=warehouse_out_of_stock_products_kb(products, page=0)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_show_out_of_stock_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_out_of_stock_page_"))
async def warehouse_out_of_stock_page_callback(callback: CallbackQuery, session: AsyncSession):
    """Пагинация для товаров без остатков"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        page = int(callback.data.split("_")[-1])
        warehouse_service = WarehouseService(session)
        products = await warehouse_service.get_all_products()
        
        from keyboards.warehouse_keyboards import warehouse_out_of_stock_products_kb
        
        await callback.message.edit_text(
            "🔴 <b>Товары без остатков</b>\n\n"
            "Эти товары закончились и требуют пополнения:",
            reply_markup=warehouse_out_of_stock_products_kb(products, page=page)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_out_of_stock_page_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_category_products_with_stock_"))
async def warehouse_category_products_with_stock_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать товары категории с остатками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Парсим category_id и page из callback_data
        parts = callback.data.split("_")
        category_id = int(parts[-2])
        page = int(parts[-1])
        
        warehouse_service = WarehouseService(session)
        category = await warehouse_service.get_category_by_id(category_id)
        products = await warehouse_service.get_products_by_category(category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        from keyboards.warehouse_keyboards import warehouse_category_products_with_stock_kb
        
        await callback.message.edit_text(
            f"📂 <b>{category.name}</b>\n\n"
            "Товары с остатками в категории:",
            reply_markup=warehouse_category_products_with_stock_kb(
                products, category_id, category.name, page
            )
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_category_products_with_stock_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_category_stock_page_"))
async def warehouse_category_stock_page_callback(callback: CallbackQuery, session: AsyncSession):
    """Пагинация для товаров категории с остатками"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        # Парсим category_id и page из callback_data
        parts = callback.data.split("_")
        category_id = int(parts[-2])
        page = int(parts[-1])
        
        warehouse_service = WarehouseService(session)
        category = await warehouse_service.get_category_by_id(category_id)
        products = await warehouse_service.get_products_by_category(category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        from keyboards.warehouse_keyboards import warehouse_category_products_with_stock_kb
        
        await callback.message.edit_text(
            f"📂 <b>{category.name}</b>\n\n"
            "Товары с остатками в категории:",
            reply_markup=warehouse_category_products_with_stock_kb(
                products, category_id, category.name, page
            )
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_category_stock_page_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_product_out_of_stock_"))
async def warehouse_product_out_of_stock_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик для товаров без остатков"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        product_id = int(callback.data.split("_")[-1])
        warehouse_service = WarehouseService(session)
        product = await warehouse_service.get_product_by_id(product_id)
        
        if not product:
            await callback.answer("❌ Товар не найден", show_alert=True)
            return
        
        # Показываем информацию о товаре без остатков
        text = f"🔴 <b>{product.name}</b>\n\n"
        text += f"💰 Цена: <b>{product.price:.2f}₽</b>\n"
        text += f"📂 Категория: <b>{product.category.name}</b>\n"
        text += f"📦 Остаток: <b>0</b> (закончился)\n"
        text += f"📊 Продано: <b>{product.total_sold}</b>\n\n"
        text += "💡 <i>Этот товар закончился и требует пополнения остатков</i>"
        
        from keyboards.warehouse_keyboards import warehouse_error_recovery_kb
        
        await callback.message.edit_text(
            text,
            reply_markup=warehouse_error_recovery_kb(
                category_id=product.category_id,
                action_type="add_stock"
            )
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_product_out_of_stock_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_stock_summary")
async def warehouse_stock_summary_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать сводку по остаткам"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        warehouse_service = WarehouseService(session)
        categories = await warehouse_service.get_categories()
        
        # Подготавливаем статистику по категориям
        category_stats = []
        for category in categories:
            products = await warehouse_service.get_products_by_category(category.id)
            
            available_products = sum(1 for p in products if p.is_unlimited or p.stock_quantity > 0)
            out_of_stock_products = sum(1 for p in products if not p.is_unlimited and p.stock_quantity <= 0)
            total_stock = sum(p.stock_quantity for p in products if not p.is_unlimited)
            
            category_stats.append({
                'id': category.id,
                'name': category.name,
                'available_products': available_products,
                'out_of_stock_products': out_of_stock_products,
                'total_stock': total_stock
            })
        
        from keyboards.warehouse_keyboards import warehouse_stock_summary_kb
        
        await callback.message.edit_text(
            "📊 <b>Сводка по остаткам</b>\n\n"
            "Обзор товаров по категориям:",
            reply_markup=warehouse_stock_summary_kb(category_stats)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_stock_summary_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_category_stock_summary_"))
async def warehouse_category_stock_summary_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать сводку по остаткам конкретной категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        category_id = int(callback.data.split("_")[-1])
        warehouse_service = WarehouseService(session)
        category = await warehouse_service.get_category_by_id(category_id)
        products = await warehouse_service.get_products_by_category(category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Подготавливаем статистику
        available_products = [p for p in products if p.is_unlimited or p.stock_quantity > 0]
        out_of_stock_products = [p for p in products if not p.is_unlimited and p.stock_quantity <= 0]
        total_stock = sum(p.stock_quantity for p in products if not p.is_unlimited)
        
        text = f"📊 <b>Сводка по остаткам: {category.name}</b>\n\n"
        text += f"📦 Всего товаров: <b>{len(products)}</b>\n"
        text += f"🟢 Доступно: <b>{len(available_products)}</b>\n"
        text += f"🔴 Закончилось: <b>{len(out_of_stock_products)}</b>\n"
        text += f"📊 Общий остаток: <b>{total_stock}</b> шт.\n\n"
        
        if available_products:
            text += "🟢 <b>Доступные товары:</b>\n"
            for product in available_products[:5]:  # Показываем первые 5
                stock_info = "∞" if product.is_unlimited else str(product.stock_quantity)
                text += f"• {product.name} ({stock_info} шт.)\n"
            
            if len(available_products) > 5:
                text += f"• ... и еще {len(available_products) - 5} товаров\n"
        
        if out_of_stock_products:
            text += "\n🔴 <b>Закончившиеся товары:</b>\n"
            for product in out_of_stock_products[:3]:  # Показываем первые 3
                text += f"• {product.name}\n"
            
            if len(out_of_stock_products) > 3:
                text += f"• ... и еще {len(out_of_stock_products) - 3} товаров\n"
        
        from keyboards.warehouse_keyboards import warehouse_error_recovery_kb
        
        await callback.message.edit_text(
            text,
            reply_markup=warehouse_error_recovery_kb(
                category_id=category_id,
                action_type="stock_summary"
            )
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_category_stock_summary_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_add_stock")
async def warehouse_add_stock_callback(callback: CallbackQuery):
    """Заглушка для добавления остатков"""
    await callback.answer("🚧 Функция добавления остатков в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_import_stock")
async def warehouse_import_stock_callback(callback: CallbackQuery):
    """Заглушка для импорта остатков"""
    await callback.answer("🚧 Функция импорта остатков в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_stock_notifications")
async def warehouse_stock_notifications_callback(callback: CallbackQuery):
    """Заглушка для настроек уведомлений об остатках"""
    await callback.answer("🚧 Настройки уведомлений об остатках в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_sales_stats")
async def warehouse_sales_stats_callback(callback: CallbackQuery):
    """Заглушка для статистики продаж"""
    await callback.answer("🚧 Статистика продаж в разработке!", show_alert=True)


@warehouse_router.callback_query(F.data == "warehouse_show_more_products")
async def warehouse_show_more_products_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать больше товаров в быстром выборе"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        warehouse_service = WarehouseService(session)
        products = await warehouse_service.get_all_products()
        
        from keyboards.warehouse_keyboards import warehouse_quick_stock_select_kb
        
        await callback.message.edit_text(
            "🎯 <b>Выбор товара для выдачи</b>\n\n"
            "Выберите товар из списка:",
            reply_markup=warehouse_quick_stock_select_kb(products, action="give")
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_show_more_products_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@warehouse_router.callback_query(F.data.startswith("warehouse_show_category_out_of_stock_"))
async def warehouse_show_category_out_of_stock_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать товары без остатков в конкретной категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    try:
        category_id = int(callback.data.split("_")[-1])
        warehouse_service = WarehouseService(session)
        category = await warehouse_service.get_category_by_id(category_id)
        products = await warehouse_service.get_products_by_category(category_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        # Фильтруем только товары без остатков
        out_of_stock_products = [p for p in products if not p.is_unlimited and p.stock_quantity <= 0]
        
        from keyboards.warehouse_keyboards import warehouse_out_of_stock_products_kb
        
        await callback.message.edit_text(
            f"🔴 <b>Товары без остатков в категории: {category.name}</b>\n\n"
            "Эти товары закончились и требуют пополнения:",
            reply_markup=warehouse_out_of_stock_products_kb(out_of_stock_products, page=0, category_id=category_id)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in warehouse_show_category_out_of_stock_callback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)