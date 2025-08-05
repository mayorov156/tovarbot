from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
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
from utils.states import AdminSettingsStates
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
    """Показать расширенную статистику администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    # Получаем статистику
    from repositories import UserRepository, OrderRepository
    from services.warehouse_service import WarehouseService
    from sqlalchemy import select, func
    from database.models import Order, OrderStatus, Product
    from datetime import datetime, timedelta
    
    user_repo = UserRepository(session)
    order_repo = OrderRepository(session)
    warehouse_service = WarehouseService(session)
    
    # Базовая статистика
    user_stats = await user_repo.get_stats()
    order_stats = await order_repo.get_orders_stats(30)
    
    # Статистика по заказам с детализацией по статусам
    total_orders = await session.scalar(select(func.count(Order.id)))
    pending_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING.value))
    paid_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PAID.value))
    delivered_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED.value))
    cancelled_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.CANCELLED.value))
    
    # Статистика по выдачам товаров со склада
    warehouse_history = await warehouse_service.get_warehouse_history(100)
    given_products_count = len([log for log in warehouse_history if log.action == "give_product"])
    
    # Доходы
    total_revenue = await session.scalar(
        select(func.sum(Order.total_price)).where(Order.status == OrderStatus.DELIVERED.value)
    ) or 0
    
    pending_revenue = await session.scalar(
        select(func.sum(Order.total_price)).where(Order.status == OrderStatus.PENDING.value)
    ) or 0
    
    # Статистика товаров
    warehouse_stats = await warehouse_service.get_smart_warehouse_stats()
    
    # Топ покупателей (последние 30 дней)  
    month_ago = datetime.now() - timedelta(days=30)
    top_buyers = await user_repo.get_top_buyers(5)
    
    # Формируем детальный отчет
    text = "📊 <b>Панель администратора</b>\n\n"
    
    # Основные показатели
    text += f"👥 <b>Пользователи:</b>\n"
    text += f"• Всего: {user_stats['total_users']}\n"
    text += f"• Активных покупателей: {user_stats['active_users']}\n"
    text += f"• Общий баланс: {user_stats['total_balance']:.2f}₽\n\n"
    
    # Статистика заказов
    text += f"📦 <b>Заказы (всего: {total_orders or 0}):</b>\n"
    text += f"• ⏳ Ожидающих: {pending_orders or 0}\n"
    text += f"• 💳 Оплаченных: {paid_orders or 0}\n"
    text += f"• ✅ Выданных: {delivered_orders or 0}\n"
    text += f"• ❌ Отмененных: {cancelled_orders or 0}\n\n"
    
    # Статистика выдач со склада
    text += f"🏪 <b>Склад:</b>\n"
    text += f"• Товаров: {warehouse_stats['general']['total_products']}\n"
    text += f"• Категорий: {warehouse_stats['general']['total_categories']}\n"
    text += f"• Выдано админом: {given_products_count}\n"
    if warehouse_stats['overflow']['total_overflow_products'] > 0:
        text += f"• ⚠️ Дубликатов: {warehouse_stats['overflow']['total_overflow_products']}\n"
    text += "\n"
    
    # Финансовая статистика
    text += f"💰 <b>Финансы:</b>\n"
    text += f"• Общий доход: {total_revenue:.2f}₽\n"
    text += f"• Ожидается: {pending_revenue:.2f}₽\n"
    if order_stats.get('monthly_revenue'):
        text += f"• За месяц: {order_stats['monthly_revenue']:.2f}₽\n"
    text += "\n"
    
    # Топ покупателей
    if top_buyers:
        text += f"🏆 <b>Топ покупателей:</b>\n"
        for i, buyer in enumerate(top_buyers, 1):
            name = buyer.first_name or "Пользователь"
            username = f"@{buyer.username}" if buyer.username else ""
            text += f"{i}. {name} {username}\n"
            text += f"   💰 {buyer.total_spent:.2f}₽ • 📦 {buyer.total_orders} заказов\n"
        text += "\n"
    
    # Активность за последние дни
    if order_stats.get('recent_orders'):
        text += f"📈 <b>Активность (7 дней):</b>\n"
        text += f"• Новых заказов: {order_stats.get('recent_orders', 0)}\n"
        text += f"• Доход: {order_stats.get('recent_revenue', 0):.2f}₽\n"
    
    # Предупреждения
    warnings = []
    if pending_orders and pending_orders > 5:
        warnings.append(f"⚠️ Много ожидающих заказов ({pending_orders})")
    
    if warehouse_stats['overflow']['total_overflow_products'] > 0:
        warnings.append(f"⚠️ Найдены дублирующиеся товары ({warehouse_stats['overflow']['total_overflow_products']})")
    
    if user_stats['total_balance'] > 10000:
        warnings.append(f"💰 Высокий общий баланс пользователей ({user_stats['total_balance']:.0f}₽)")
    
    if warnings:
        text += f"\n🚨 <b>Требует внимания:</b>\n"
        for warning in warnings:
            text += f"• {warning}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("admin_menu")
    )
    await callback.answer()





# admin_categories удален - упрощена админ-панель


@admin_router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: CallbackQuery, session: AsyncSession):
    """Главное меню настроек системы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from services.settings_service import SettingsService
    
    settings_service = SettingsService(session)
    
    # Инициализируем настройки по умолчанию при первом заходе
    await settings_service.initialize_default_settings()
    
    # Получаем количество настроек по категориям
    categories = await settings_service.get_categories()
    total_settings = len(await settings_service.get_editable_settings())
    
    text = (
        "⚙️ <b>Настройки системы</b>\n\n"
        "Здесь вы можете изменять параметры бота через удобный интерфейс:\n\n"
        f"📊 <b>Доступно настроек:</b> {total_settings}\n"
        f"📂 <b>Категорий:</b> {len(categories)}\n\n"
        "Выберите категорию настроек или просмотрите все:"
    )
    
    from keyboards.inline_keyboards import admin_settings_menu_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_settings_menu_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_settings_category_"))
async def admin_settings_category_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать настройки категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    category = callback.data.split("_")[-1]
    
    from services.settings_service import SettingsService
    from keyboards.inline_keyboards import admin_settings_category_kb, admin_settings_back_kb
    
    settings_service = SettingsService(session)
    settings = await settings_service.get_editable_settings(category)
    
    if not settings:
        await callback.message.edit_text(
            f"📂 <b>Категория: {category.title()}</b>\n\n❌ Настройки в данной категории не найдены.",
            reply_markup=admin_settings_back_kb()
        )
        return
    
    category_names = {
        "referral": "💰 Реферальная система",
        "contacts": "📞 Контакты", 
        "messages": "💬 Сообщения",
       "financial": "💳 Финансы"
    }
    
    text = f"{category_names.get(category, f'📂 {category.title()}')}\n\n"
    text += f"Найдено настроек: {len(settings)}\n\nВыберите настройку для редактирования:"
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_settings_category_kb(settings, category)
    )
    await callback.answer()


# @admin_router.callback_query(F.data == "admin_settings_all")
# async def admin_settings_all_callback(callback: CallbackQuery, session: AsyncSession):
#     """Показать все настройки"""
#     if not is_admin(callback.from_user.id):
#         await callback.answer("❌ У вас нет прав доступа", show_alert=True)
#         return
#     
#     from services.settings_service import SettingsService
#     from keyboards.inline_keyboards import admin_settings_category_kb, admin_settings_back_kb
#     
#     settings_service = SettingsService(session)
#     settings = await settings_service.get_editable_settings()
#     
#     if not settings:
#         await callback.message.edit_text(
#             "📋 <b>Все настройки</b>\n\n❌ Настройки не найдены.",
#             reply_markup=admin_settings_back_kb()
#         )
#         return
#     
#     await callback.message.edit_text(
#         f"📋 <b>Все настройки</b>\n\nВсего настроек: {len(settings)}\n\nВыберите настройку для редактирования:",
#         reply_markup=admin_settings_category_kb(settings, "all")
#     )
#     await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_setting_edit_"))
async def admin_setting_edit_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать интерфейс редактирования настройки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    setting_id = int(callback.data.split("_")[-1])
    
    from services.settings_service import SettingsService
    from keyboards.inline_keyboards import admin_setting_edit_kb, admin_settings_back_kb
    
    settings_service = SettingsService(session)
    setting = await settings_service.get_setting_by_id(setting_id)
    
    if not setting:
        await callback.message.edit_text(
            "❌ Настройка не найдена",
            reply_markup=admin_settings_back_kb()
        )
        return
    
    # Форматируем значение для отображения
    current_value = setting.value
    if setting.value_type == "bool":
        current_value = "✅ Включено" if setting.value.lower() in ("true", "1", "yes", "on") else "❌ Выключено"
    
    text = (
        f"⚙️ <b>Настройка: {setting.description or setting.key}</b>\n\n"
        f"🔑 <b>Ключ:</b> <code>{setting.key}</code>\n"
        f"📋 <b>Категория:</b> {setting.category}\n"
        f"🔤 <b>Тип:</b> {setting.value_type}\n"
        f"💾 <b>Текущее значение:</b>\n<code>{current_value}</code>\n\n"
    )
    
    if setting.description:
        text += f"📝 <b>Описание:</b> {setting.description}"
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_setting_edit_kb(setting)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_setting_change_"))
async def admin_setting_change_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать изменение значения настройки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    setting_id = int(callback.data.split("_")[-1])
    
    from services.settings_service import SettingsService
    from keyboards.inline_keyboards import admin_settings_back_kb
    
    settings_service = SettingsService(session)
    setting = await settings_service.get_setting_by_id(setting_id)
    
    if not setting:
        await callback.message.edit_text(
            "❌ Настройка не найдена",
            reply_markup=admin_settings_back_kb()
        )
        return
    
    await state.update_data(setting_id=setting_id)
    await state.set_state(AdminSettingsStates.waiting_for_value)
    
    # Подсказки для разных типов
    type_hints = {
        "string": "Введите текстовое значение:",
        "int": "Введите целое число:",
        "float": "Введите число (можно с десятичной точкой):",
        "bool": "Введите true/false, 1/0, yes/no, on/off:"
    }
    
    hint = type_hints.get(setting.value_type, "Введите новое значение:")
    
    text = (
        f"✏️ <b>Изменение настройки</b>\n\n"
        f"⚙️ <b>Настройка:</b> {setting.description or setting.key}\n"
        f"💾 <b>Текущее значение:</b> <code>{setting.value}</code>\n"
        f"🔤 <b>Тип:</b> {setting.value_type}\n\n"
        f"{hint}"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_setting_edit_{setting_id}")
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin_setting_toggle_"))
async def admin_setting_toggle_callback(callback: CallbackQuery, session: AsyncSession):
    """Переключить boolean настройку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    setting_id = int(callback.data.split("_")[-1])
    
    from services.settings_service import SettingsService
    settings_service = SettingsService(session)
    
    setting = await settings_service.get_setting_by_id(setting_id)
    if not setting or setting.value_type != "bool":
        await callback.answer("❌ Настройка не найдена или не является логической", show_alert=True)
        return
    
    # Переключаем значение
    current_value = setting.value.lower() in ("true", "1", "yes", "on")
    new_value = not current_value
    
    success = await settings_service.set_setting(setting.key, new_value)
    
    if success:
        await callback.answer(f"✅ Настройка обновлена: {new_value}")
        # Обновляем отображение
        await admin_setting_edit_callback(callback, session)
    else:
        await callback.answer("❌ Ошибка при обновлении настройки", show_alert=True)


@admin_router.message(AdminSettingsStates.waiting_for_value)
async def admin_setting_value_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка нового значения настройки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа")
        return
    
    data = await state.get_data()
    setting_id = data.get("setting_id")
    
    from services.settings_service import SettingsService
    settings_service = SettingsService(session)
    
    setting = await settings_service.get_setting_by_id(setting_id)
    if not setting:
        await message.answer("❌ Настройка не найдена")
        await state.clear()
        return
    
    new_value = message.text.strip()
    
    # Валидация значения
    try:
        if setting.value_type == "int":
            int(new_value)
        elif setting.value_type == "float":
            float(new_value)
        elif setting.value_type == "bool":
            if new_value.lower() not in ("true", "false", "1", "0", "yes", "no", "on", "off"):
                raise ValueError("Неверное boolean значение")
    except ValueError:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        await message.answer(
            f"❌ Неверный формат значения для типа {setting.value_type}.\n\n"
            f"Попробуйте еще раз или нажмите Отмена.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_setting_edit_{setting_id}")
            ).as_markup()
        )
        return
    
    await state.update_data(new_value=new_value)
    await state.set_state(AdminSettingsStates.waiting_for_confirmation)
    
    # Показываем превью изменения
    old_display = setting.value
    new_display = new_value
    
    if setting.value_type == "bool":
        old_display = "✅ Включено" if setting.value.lower() in ("true", "1", "yes", "on") else "❌ Выключено"
        new_display = "✅ Включено" if new_value.lower() in ("true", "1", "yes", "on") else "❌ Выключено"
    
    text = (
        f"🔄 <b>Подтверждение изменения</b>\n\n"
        f"⚙️ <b>Настройка:</b> {setting.description or setting.key}\n\n"
        f"📥 <b>Старое значение:</b>\n<code>{old_display}</code>\n\n"
        f"📤 <b>Новое значение:</b>\n<code>{new_display}</code>\n\n"
        f"❓ Сохранить изменения?"
    )
    
    from keyboards.inline_keyboards import admin_setting_confirm_kb
    
    await message.answer(
        text,
        reply_markup=admin_setting_confirm_kb(setting_id)
    )


@admin_router.callback_query(F.data.startswith("admin_setting_confirm_"))
async def admin_setting_confirm_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтвердить изменение настройки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    setting_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    new_value = data.get("new_value")
    
    if not new_value:
        await callback.answer("❌ Не найдено новое значение", show_alert=True)
        return
    
    from services.settings_service import SettingsService
    from keyboards.inline_keyboards import admin_settings_back_kb
    
    settings_service = SettingsService(session)
    setting = await settings_service.get_setting_by_id(setting_id)
    
    if not setting:
        await callback.message.edit_text(
            "❌ Настройка не найдена",
            reply_markup=admin_settings_back_kb()
        )
        await state.clear()
        return
    
    # Конвертируем значение к нужному типу
    converted_value = new_value
    if setting.value_type == "int":
        converted_value = int(new_value)
    elif setting.value_type == "float":
        converted_value = float(new_value)
    elif setting.value_type == "bool":
        converted_value = new_value.lower() in ("true", "1", "yes", "on")
    
    success = await settings_service.set_setting(setting.key, converted_value)
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Настройка успешно обновлена!</b>\n\n"
            f"⚙️ <b>Настройка:</b> {setting.description or setting.key}\n"
            f"💾 <b>Новое значение:</b> <code>{new_value}</code>\n\n"
            f"Изменения вступили в силу немедленно.",
            reply_markup=admin_settings_back_kb()
        )
        await callback.answer("✅ Настройка обновлена!")
    else:
        await callback.message.edit_text(
            "❌ Ошибка при сохранении настройки. Попробуйте еще раз.",
            reply_markup=admin_settings_back_kb()
        )
        await callback.answer("❌ Ошибка сохранения", show_alert=True)
    
    await state.clear()


@admin_router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery, session: AsyncSession):
    """Главное меню управления пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from repositories import UserRepository
    user_repo = UserRepository(session)
    
    # Получаем общую статистику
    stats = await user_repo.get_stats()
    
    text = (
        "👥 <b>Управление пользователями</b>\n\n"
        "📊 <b>Общие показатели:</b>\n"
        f"• Всего пользователей: {stats['total_users']}\n"
        f"• Активных покупателей: {stats['active_users']}\n"
        f"• Общий баланс: {stats['total_balance']:.2f}₽\n\n"
        "Выберите раздел для просмотра:"
    )
    
    from keyboards.inline_keyboards import admin_users_menu_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_users_menu_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users_top_buyers")
async def admin_users_top_buyers_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать топ покупателей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from repositories import UserRepository
    user_repo = UserRepository(session)
    top_buyers = await user_repo.get_top_buyers(10)
    
    text = "🏆 <b>Топ покупателей</b>\n\n"
    
    if top_buyers:
        for i, user in enumerate(top_buyers, 1):
            name = user.first_name or "Пользователь"
            username = f"@{user.username}" if user.username else ""
            text += f"{i}. {name} {username}\n"
            text += f"   💰 Потрачено: {user.total_spent:.2f}₽\n"
            text += f"   📦 Заказов: {user.total_orders}\n\n"
    else:
        text += "📭 Пока нет покупателей"
    
    from keyboards.inline_keyboards import admin_users_back_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_users_back_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users_active")
async def admin_users_active_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать активных пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from repositories import UserRepository
    user_repo = UserRepository(session)
    active_users = await user_repo.get_active_users(10)
    
    text = "📈 <b>Самые активные пользователи</b>\n\n"
    
    if active_users:
        for i, user in enumerate(active_users, 1):
            name = user.first_name or "Пользователь"
            username = f"@{user.username}" if user.username else ""
            text += f"{i}. {name} {username}\n"
            text += f"   📦 Заказов: {user.total_orders}\n"
            text += f"   💰 Потрачено: {user.total_spent:.2f}₽\n\n"
    else:
        text += "📭 Пока нет активных пользователей"
    
    from keyboards.inline_keyboards import admin_users_back_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_users_back_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users_recent")
async def admin_users_recent_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать новых пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from repositories import UserRepository
    user_repo = UserRepository(session)
    recent_users = await user_repo.get_recent_users(10)
    
    text = "🆕 <b>Новые пользователи (за 7 дней)</b>\n\n"
    
    if recent_users:
        for i, user in enumerate(recent_users, 1):
            name = user.first_name or "Пользователь"
            username = f"@{user.username}" if user.username else ""
            reg_date = user.created_at.strftime("%d.%m.%Y %H:%M") if hasattr(user, 'created_at') and user.created_at else "Дата неизвестна"
            text += f"{i}. {name} {username}\n"
            text += f"   📅 Регистрация: {reg_date}\n"
            text += f"   📦 Заказов: {user.total_orders}\n\n"
    else:
        text += "📭 Нет новых пользователей за последние 7 дней"
    
    from keyboards.inline_keyboards import admin_users_back_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_users_back_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users_balance")
async def admin_users_balance_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать пользователей с балансом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from repositories import UserRepository
    user_repo = UserRepository(session)
    users_with_balance = await user_repo.get_users_with_balance(10)
    
    text = "💰 <b>Пользователи с балансом</b>\n\n"
    
    if users_with_balance:
        total_balance = sum(user.balance for user in users_with_balance)
        text += f"💳 <b>Общий баланс топ-{len(users_with_balance)}: {total_balance:.2f}₽</b>\n\n"
        
        for i, user in enumerate(users_with_balance, 1):
            name = user.first_name or "Пользователь"
            username = f"@{user.username}" if user.username else ""
            text += f"{i}. {name} {username}\n"
            text += f"   💰 Баланс: {user.balance:.2f}₽\n"
            text += f"   📦 Заказов: {user.total_orders}\n\n"
    else:
        text += "📭 Нет пользователей с положительным балансом"
    
    from keyboards.inline_keyboards import admin_users_back_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_users_back_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users_stats")
async def admin_users_stats_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать детальную статистику пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from repositories import UserRepository
    from sqlalchemy import select, func
    from database.models import User
    
    user_repo = UserRepository(session)
    stats = await user_repo.get_stats()
    
    # Дополнительная статистика
    users_with_orders = await session.scalar(select(func.count(User.id)).where(User.total_orders > 0))
    users_with_balance = await session.scalar(select(func.count(User.id)).where(User.balance > 0))
    avg_orders = await session.scalar(select(func.avg(User.total_orders)).where(User.total_orders > 0)) or 0
    avg_spent = await session.scalar(select(func.avg(User.total_spent)).where(User.total_spent > 0)) or 0
    
    # Получаем пользователей за последние дни
    from datetime import datetime, timedelta
    recent_users_count = await session.scalar(
        select(func.count(User.id)).where(
            User.created_at >= datetime.now() - timedelta(days=7)
        )
    ) if hasattr(User, 'created_at') else 0
    
    text = (
        "📊 <b>Детальная статистика пользователей</b>\n\n"
        f"👥 <b>Общие показатели:</b>\n"
        f"• Всего пользователей: {stats['total_users']}\n"
        f"• С заказами: {users_with_orders or 0} ({(users_with_orders or 0) / max(stats['total_users'], 1) * 100:.1f}%)\n"
        f"• С балансом: {users_with_balance or 0}\n"
        f"• Новых за неделю: {recent_users_count or 0}\n\n"
        f"💰 <b>Финансовые показатели:</b>\n"
        f"• Общий оборот: {sum(u.total_spent for u in await user_repo.get_top_buyers(1000)):.2f}₽\n"
        f"• Общий баланс: {stats['total_balance']:.2f}₽\n"
        f"• Средняя сумма заказа: {avg_spent:.2f}₽\n\n"
        f"📈 <b>Активность:</b>\n"
        f"• Среднее количество заказов: {avg_orders:.1f}\n"
        f"• Конверсия в покупатели: {(users_with_orders or 0) / max(stats['total_users'], 1) * 100:.1f}%"
    )
    
    from keyboards.inline_keyboards import admin_users_back_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_users_back_kb()
    )
    await callback.answer()


# ================== СКЛАД ТОВАРОВ ==================

@admin_router.callback_query(F.data == "warehouse_menu")
async def warehouse_menu_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать классическое главное меню склада"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from services.warehouse_service import WarehouseService 
    
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

    text = (
        f"🏪 <b>Управление складом товаров</b>\n\n"
        f"📊 <b>Общая статистика:</b>\n"
        f"• Категорий: {len(category_stats)}\n"
        f"• Товаров: {total_products}\n"
        f"• Остаток: {stock_display} шт.\n\n"
        f"💡 Выберите действие для управления складом:"
    )
    
    await callback.message.edit_text(
        text,
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
    """Умная статистика остатков товаров с анализом переполненных товаров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав доступа", show_alert=True)
        return
    
    from services.warehouse_service import WarehouseService
    warehouse_service = WarehouseService(session)
    smart_stats = await warehouse_service.get_smart_warehouse_stats()
    
    general = smart_stats['general']
    overflow = smart_stats['overflow']
    
    if general['total_products'] == 0:
        await callback.message.edit_text(
            "📊 <b>Умная статистика склада</b>\n\n"
            "❌ Нет товаров для отображения статистики",
            reply_markup=back_button("warehouse_menu")
        )
        await callback.answer()
        return
    
    # Формируем умную статистику
    text = "📊 <b>Умная статистика склада</b>\n\n"
    
    # Общие показатели
    text += f"📂 <b>Общие показатели:</b>\n"
    text += f"• Категорий: {general['total_categories']}\n"
    text += f"• Товаров: {general['total_products']}\n"
    
    # Остатки
    stock_info = []
    if general['total_unlimited'] > 0:
        stock_info.append(f"∞x{general['total_unlimited']}")
    if general['total_stock'] > 0:
        stock_info.append(str(general['total_stock']))
    
    stock_display = " + ".join(stock_info) if stock_info else "0"
    text += f"• Остатки: {stock_display} шт.\n\n"
    
    # Анализ переполненных товаров
    if overflow['total_overflow_products'] > 0:
        text += f"⚠️ <b>Анализ дубликатов:</b>\n"
        text += f"• Категорий с дубликатами: {overflow['categories_with_overflow']}\n"
        text += f"• Переполненных товаров: {overflow['total_overflow_products']}\n\n"
        
        # Показываем топ переполненных товаров
        if overflow['top_overflow']:
            text += f"🔥 <b>Самые переполненные товары:</b>\n"
            for i, item in enumerate(overflow['top_overflow'][:5], 1):
                name = item['name']
                count = item['count']
                
                # Показываем детали каждого дубликата
                products_info = []
                for product in item['products']:
                    if product['is_unlimited']:
                        products_info.append(f"#{product['id']}:∞")
                    else:
                        products_info.append(f"#{product['id']}:{product['stock']}")
                
                products_display = ", ".join(products_info)
                
                # Общий остаток
                total_display = ""
                if item['has_unlimited']:
                    unlimited_count = sum(1 for p in item['products'] if p['is_unlimited'])
                    total_display += f"∞x{unlimited_count}"
                if item['total_stock'] > 0:
                    if total_display:
                        total_display += f" + {item['total_stock']}"
                    else:
                        total_display = str(item['total_stock'])
                
                text += f"{i}. ⚠️ <b>{name}</b> ({total_display})\n"
                text += f"   🔢 Дубликатов: {count} ({products_display})\n"
                
                if i < len(overflow['top_overflow'][:5]):
                    text += "\n"
            
            if len(overflow['top_overflow']) > 5:
                text += f"\n... и еще {len(overflow['top_overflow']) - 5} переполненных товаров"
    else:
        text += "✅ <b>Дубликаты не обнаружены</b>\n\n"
        text += "💡 Все товары имеют уникальные названия"
    
    # Рекомендации
    if overflow['total_overflow_products'] > 0:
        text += "\n\n💡 <b>Рекомендации:</b>\n"
        text += "• Объедините дублирующиеся товары\n"
        text += "• Используйте единые названия\n"
        text += "• Удалите неактуальные позиции"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("warehouse_menu")
    )
    await callback.answer()