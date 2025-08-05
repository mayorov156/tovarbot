from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession


from services import OrderService, ProductService, UserService
from keyboards import admin_menu_kb, admin_orders_kb, order_management_kb, back_button
from utils import format_order_info, format_stats, AdminStates
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


@admin_router.callback_query(F.data == "admin_products")
async def admin_products_callback(callback: CallbackQuery):
    """Управление товарами (заглушка)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    text = "🛍 <b>Управление товарами</b>\n\n"
    text += "Функционал в разработке.\n"
    text += "Для управления товарами используйте базу данных напрямую."
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("admin_menu")
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_categories")
async def admin_categories_callback(callback: CallbackQuery):
    """Управление категориями (заглушка)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    text = "📂 <b>Управление категориями</b>\n\n"
    text += "Функционал в разработке.\n"
    text += "Для управления категориями используйте базу данных напрямую."
    
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