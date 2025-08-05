from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession


from services import OrderService, ProductService, UserService
from keyboards import (
    admin_menu_kb, admin_orders_kb, order_management_kb, back_button,
    warehouse_menu_kb, warehouse_products_kb, warehouse_product_actions_kb,
    warehouse_categories_kb
)
from utils import format_order_info, format_stats, AdminStates
from repositories import CategoryRepository
from config import settings

admin_router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in settings.ADMIN_IDS





@admin_router.message(Command("admin"))
async def admin_menu_command(message: Message):
    """Админ панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    await message.answer(
        "⚙️ <b>Админ панель</b>",
        reply_markup=admin_menu_kb()
    )


@admin_router.callback_query(F.data == "admin_menu")
async def admin_menu_callback(callback: CallbackQuery):
    """Показать админ меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Админ панель</b>",
        reply_markup=admin_menu_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_orders")
async def admin_orders_callback(callback: CallbackQuery, session: AsyncSession ):
    """Показать заказы для админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    order_service = OrderService(session)
    orders = await order_service.get_pending_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📦 Нет заказов в ожидании",
            reply_markup=back_button("admin_menu")
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📦 Заказы в ожидании:",
        reply_markup=admin_orders_kb(orders)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_order_"))
async def admin_order_details(callback: CallbackQuery, session: AsyncSession ):
    """Детали заказа для админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    order_service = OrderService(session)
    order = await order_service.get_order_details(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    text = "⚙️ <b>Управление заказом</b>\n\n"
    text += format_order_info(order)
    text += f"\n👤 Пользователь: {order.user.first_name}"
    if order.user.username:
        text += f" (@{order.user.username})"
    
    await callback.message.edit_text(
        text,
        reply_markup=order_management_kb(order)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("deliver_order_"))
async def deliver_order_callback(callback: CallbackQuery, state: FSMContext):
    """Начать процесс выдачи заказа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    await state.update_data(order_id=order_id)
    await state.set_state(AdminStates.waiting_for_order_content)
    
    await callback.message.edit_text(
        "📋 Введите содержимое для выдачи заказа:\n"
        "(ключи, коды, инструкции и т.д.)",
        reply_markup=back_button("admin_orders")
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_order_content)
async def process_order_delivery(message: Message, state: FSMContext, session: AsyncSession ):
    """Обработать выдачу заказа"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    data = await state.get_data()
    order_id = data.get("order_id")
    digital_content = message.text
    
    order_service = OrderService(session)
    success, result_message = await order_service.deliver_order(
        order_id, digital_content, message.from_user.id
    )
    
    if success:
        # Уведомляем пользователя
        order = await order_service.get_order_details(order_id)
        user_text = "✅ <b>Ваш заказ выдан!</b>\n\n"
        user_text += format_order_info(order, show_content=True)
        
        try:
            await message.bot.send_message(
                chat_id=order.user_id,
                text=user_text
            )
        except Exception:
            pass  # Пользователь заблокировал бота
        
        await message.answer(
            f"✅ Заказ #{order_id} успешно выдан!",
            reply_markup=admin_menu_kb()
        )
    else:
        await message.answer(f"❌ {result_message}")
    
    await state.clear()


@admin_router.callback_query(F.data.startswith("admin_cancel_order_"))
async def admin_cancel_order_callback(callback: CallbackQuery, state: FSMContext):
    """Начать отмену заказа админом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[3])
    
    await state.update_data(order_id=order_id)
    await state.set_state(AdminStates.waiting_for_cancel_reason)
    
    await callback.message.edit_text(
        "❌ Введите причину отмены заказа:",
        reply_markup=back_button("admin_orders")
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_cancel_reason)
async def process_order_cancellation(message: Message, state: FSMContext, session: AsyncSession ):
    """Обработать отмену заказа"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    data = await state.get_data()
    order_id = data.get("order_id")
    reason = message.text
    
    order_service = OrderService(session)
    success, result_message = await order_service.cancel_order(order_id, reason)
    
    if success:
        # Уведомляем пользователя
        order = await order_service.get_order_details(order_id)
        user_text = f"❌ <b>Ваш заказ #{order_id} отменен</b>\n\n"
        user_text += f"📝 Причина: {reason}\n"
        user_text += f"💰 Средства возвращены на баланс: {order.total_price:.2f}₽"
        
        try:
            await message.bot.send_message(
                chat_id=order.user_id,
                text=user_text
            )
        except Exception:
            pass  # Пользователь заблокировал бота
        
        await message.answer(
            f"✅ Заказ #{order_id} отменен!",
            reply_markup=admin_menu_kb()
        )
    else:
        await message.answer(f"❌ {result_message}")
    
    await state.clear()


@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery, session: AsyncSession ):
    """Показать статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Получаем статистику
    from repositories import UserRepository, OrderRepository
    
    user_repo = UserRepository(session)
    order_repo = OrderRepository(session)
    
    user_stats = await user_repo.get_stats()
    order_stats = await order_repo.get_orders_stats(30)
    
    combined_stats = {**user_stats, **order_stats}
    text = format_stats(combined_stats)
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("admin_menu")
    )
    await callback.answer()





# admin_categories удален - упрощена админ-панель


@admin_router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: CallbackQuery):
    """Настройки системы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    text = "⚙️ <b>Настройки системы</b>\n\n"
    text += f"🤖 ID бота: {callback.bot.id}\n"
    text += f"👥 Количество админов: {len(settings.ADMIN_IDS)}\n"
    text += f"💰 Процент с рефералов: {settings.REFERRAL_REWARD_PERCENT}%\n"
    text += f"🆘 Поддержка: @{settings.SUPPORT_USERNAME}\n"
    text += f"📢 Канал заработка: {settings.EARNING_CHANNEL}\n\n"
    text += "Для изменения настроек отредактируйте файл .env"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("admin_menu")
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery, session: AsyncSession ):
    """Управление пользователями (заглушка)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    user_service = UserService(session)
    from repositories import UserRepository
    
    user_repo = UserRepository(session)
    top_buyers = await user_repo.get_top_buyers(5)
    
    text = "👥 <b>Управление пользователями</b>\n\n"
    text += "🏆 <b>Топ покупателей:</b>\n"
    
    for i, user in enumerate(top_buyers, 1):
        name = user.first_name or "Пользователь"
        text += f"{i}. {name} - {user.total_spent:.2f}₽\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("admin_menu")
    )
    await callback.answer()


# ================== СКЛАД ТОВАРОВ ==================

@admin_router.callback_query(F.data == "warehouse_menu")
async def warehouse_menu_callback(callback: CallbackQuery):
    """Показать меню склада"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🏪 <b>Склад товаров</b>\n\n"
        "Управление товарами, остатками и выдачами",
        reply_markup=warehouse_menu_kb()
    )
    await callback.answer()


# warehouse_all_products обработчик перемещен в warehouse.py


# warehouse_by_category и warehouse_category_ обработчики удалены (больше не используются)


# warehouse_product_ обработчики перемещены в warehouse.py


# warehouse_give_ обработчики перемещены в warehouse.py


@admin_router.callback_query(F.data.startswith("warehouse_add_stock_"))
async def warehouse_add_stock_callback(callback: CallbackQuery, state: FSMContext):
    """Добавить остаток товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split("_")[-1])
    
    await state.update_data(product_id=product_id, action="add")
    await state.set_state(AdminStates.waiting_for_stock_quantity)
    
    await callback.message.edit_text(
        "📈 <b>Добавление остатка</b>\n\n"
        "Введите количество для добавления:",
        reply_markup=back_button("warehouse_menu")
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("warehouse_remove_stock_"))
async def warehouse_remove_stock_callback(callback: CallbackQuery, state: FSMContext):
    """Списать остаток товара"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split("_")[-1])
    
    await state.update_data(product_id=product_id, action="remove")
    await state.set_state(AdminStates.waiting_for_stock_quantity)
    
    await callback.message.edit_text(
        "📉 <b>Списание остатка</b>\n\n"
        "Введите количество для списания:",
        reply_markup=back_button("warehouse_menu")
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_stock_quantity)
async def process_stock_quantity(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка изменения остатка товара"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        await message.answer(
            "❌ Введите корректное количество (положительное число):",
            reply_markup=back_button("warehouse_menu")
        )
        return
    
    data = await state.get_data()
    product_id = data.get('product_id')
    action = data.get('action')
    
    product_service = ProductService(session)
    product = await product_service.get_product_by_id(product_id)
    
    if not product:
        await message.answer(
            "❌ Товар не найден",
            reply_markup=back_button("warehouse_menu")
        )
        await state.clear()
        return
    
    if product.is_unlimited:
        await message.answer(
            "❌ Нельзя изменять остатки для товаров с неограниченным количеством",
            reply_markup=back_button("warehouse_menu")
        )
        await state.clear()
        return
    
    if action == "add":
        await product_service.increase_stock(product_id, quantity)
        action_text = "добавлено"
        import logging
        logging.info(f"WAREHOUSE: Admin {message.from_user.id} added {quantity} stock to '{product.name}'")
    else:  # remove
        if product.stock_quantity < quantity:
            await message.answer(
                f"❌ Недостаточно товара для списания\n"
                f"Доступно: {product.stock_quantity}",
                reply_markup=back_button("warehouse_menu")
            )
            return
        
        await product_service.decrease_stock(product_id, quantity)
        action_text = "списано"
        import logging
        logging.info(f"WAREHOUSE: Admin {message.from_user.id} removed {quantity} stock from '{product.name}'")
    
    new_stock = await product_service.get_stock_quantity(product_id)
    
    await message.answer(
        f"✅ <b>Остаток изменен!</b>\n\n"
        f"📦 Товар: {product.name}\n"
        f"📊 {action_text.capitalize()}: {quantity}\n"
        f"📈 Новый остаток: {new_stock}",
        reply_markup=back_button("warehouse_menu")
    )
    
    await state.clear()


@admin_router.callback_query(F.data == "warehouse_history")
async def warehouse_history_callback(callback: CallbackQuery):
    """История выдач товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Здесь можно реализовать показ истории из логов или отдельной таблицы
    await callback.message.edit_text(
        "📊 <b>История выдач</b>\n\n"
        "История выдач товаров ведется в логах системы.\n"
        "Подробную информацию можно найти в файлах логов.",
        reply_markup=back_button("warehouse_menu")
    )
    await callback.answer()


@admin_router.callback_query(F.data == "warehouse_stats")
async def warehouse_stats_callback(callback: CallbackQuery, session: AsyncSession):
    """Статистика остатков товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    product_service = ProductService(session)
    products = await product_service.get_all_products()
    
    if not products:
        await callback.message.edit_text(
            "📈 <b>Статистика остатков</b>\n\n"
            "Нет товаров для отображения статистики",
            reply_markup=back_button("warehouse_menu")
        )
        await callback.answer()
        return
    
    total_products = len(products)
    in_stock = sum(1 for p in products if p.is_unlimited or p.stock_quantity > 0)
    out_of_stock = total_products - in_stock
    unlimited_products = sum(1 for p in products if p.is_unlimited)
    
    total_stock_value = sum(
        p.price * p.stock_quantity 
        for p in products 
        if not p.is_unlimited
    )
    
    text = "📈 <b>Статистика остатков</b>\n\n"
    text += f"📦 Всего товаров: {total_products}\n"
    text += f"🟢 В наличии: {in_stock}\n"
    text += f"🔴 Нет в наличии: {out_of_stock}\n"
    text += f"♾️ Неограниченные: {unlimited_products}\n\n"
    text += f"💰 Стоимость остатков: {total_stock_value:.2f}₽\n\n"
    
    text += "<b>Товары с низкими остатками:</b>\n"
    low_stock = [p for p in products if not p.is_unlimited and 0 < p.stock_quantity <= 5]
    
    if low_stock:
        for product in low_stock[:5]:  # Показываем только первые 5
            text += f"⚠️ {product.name}: {product.stock_quantity}\n"
    else:
        text += "✅ Все товары в достаточном количестве"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("warehouse_menu")
    )
    await callback.answer()