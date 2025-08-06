from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession


from services import UserService, ProductService, OrderService
from keyboards import (
    main_menu_kb, categories_kb, products_kb, product_detail_kb,
    profile_kb, referrals_kb, order_confirmation_kb, user_orders_kb, back_button
)
from utils import format_user_info, format_product_info, format_order_info, OrderForm, log_user_action
from config import settings

callback_router = Router()





@callback_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "📋 Главное меню:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@callback_router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать профиль пользователя"""
    log_user_action(callback.from_user.id, "profile_view", "Открыл профиль")
    
    user_service = UserService(session)
    
    user_info = await user_service.get_user_info(callback.from_user.id)
    if not user_info:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    text = format_user_info(
        user_info["user"],
        user_info["referrals_count"]
    )
    
    await callback.message.edit_text(text, reply_markup=profile_kb())
    await callback.answer()


@callback_router.callback_query(F.data == "catalog")
async def catalog_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать каталог категорий"""
    log_user_action(callback.from_user.id, "catalog_view", "Открыл каталог")
    
    product_service = ProductService(session)
    
    categories = await product_service.get_categories_menu()
    
    if not categories:
        await callback.message.edit_text(
            "❌ Категории не найдены",
            reply_markup=back_button()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📂 Выберите категорию:",
        reply_markup=categories_kb(categories)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("category_"))
async def category_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать товары категории"""
    category_id = int(callback.data.split("_")[1])
    log_user_action(callback.from_user.id, "category_select", f"Выбрал категорию {category_id}")
    
    page = 0
    
    product_service = ProductService(session)
    products = await product_service.get_products_by_category(category_id)
    
    if not products:
        await callback.message.edit_text(
            "❌ В этой категории пока нет товаров",
            reply_markup=back_button("catalog")
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "🛍 Выберите товар:",
        reply_markup=products_kb(products, category_id, page)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("products_"))
async def products_pagination(callback: CallbackQuery, session: AsyncSession ):
    """Пагинация товаров"""
    parts = callback.data.split("_")
    category_id = int(parts[1])
    page = int(parts[2])
    
    product_service = ProductService(session)
    products = await product_service.get_products_by_category(category_id)
    
    await callback.message.edit_reply_markup(
        reply_markup=products_kb(products, category_id, page)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("product_"))
async def product_detail_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать детали товара"""
    product_id = int(callback.data.split("_")[1])
    log_user_action(callback.from_user.id, "product_view", f"Просмотрел товар {product_id}")
    
    product_service = ProductService(session)
    product = await product_service.get_product_details(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден или недоступен", show_alert=True)
        return
    
    text = format_product_info(product)
    
    await callback.message.edit_text(
        text,
        reply_markup=product_detail_kb(product, user_can_buy=True)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("buy_"))
async def buy_product_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать покупку товара"""
    try:
        product_id = int(callback.data.split("_")[1])
        print(f"🛒 DEBUG: Пользователь {callback.from_user.id} пытается купить товар {product_id}")
        log_user_action(callback.from_user.id, "buy_attempt", f"Попытка покупки товара {product_id}")
        
        # Сохраняем ID товара в состоянии
        await state.update_data(product_id=product_id)
        await state.set_state(OrderForm.waiting_for_confirmation)
        
        print(f"🛒 DEBUG: Состояние FSM установлено в waiting_for_confirmation")
    except Exception as e:
        print(f"❌ DEBUG: Ошибка в начале buy_product_callback: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)
        return
    
    try:
        order_service = OrderService(session)
        print(f"🛒 DEBUG: OrderService создан")
        
        # Создаем заказ
        print(f"🛒 DEBUG: Создаем заказ для пользователя {callback.from_user.id}, товар {product_id}")
        order, message = await order_service.create_order(
            user_id=callback.from_user.id,
            product_id=product_id,
            quantity=1
        )
        
        print(f"🛒 DEBUG: Результат создания заказа: order={order is not None}, message='{message}'")
        
        if not order:
            print(f"❌ DEBUG: Заказ не создан: {message}")
            await callback.answer(f"❌ {message}", show_alert=True)
            await state.clear()
            return
        
        # Показываем подтверждение
        print(f"🛒 DEBUG: Показываем подтверждение заказа #{order.id}")
        text = f"🛒 <b>Подтверждение заказа</b>\n\n"
        text += format_order_info(order)
        text += f"\n💰 К списанию: <b>{order.total_price:.2f}₽</b>"
        
        await callback.message.edit_text(
            text,
            reply_markup=order_confirmation_kb(order.id)
        )
        await callback.answer()
        print(f"✅ DEBUG: Подтверждение заказа отправлено успешно")
        
    except Exception as e:
        print(f"❌ DEBUG: Ошибка в buy_product_callback: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Произошла ошибка при создании заказа", show_alert=True)
        await state.clear()


@callback_router.callback_query(F.data.startswith("confirm_order_"))
async def confirm_order_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession ):
    """Подтвердить заказ"""
    order_id = int(callback.data.split("_")[2])
    
    order_service = OrderService(session)
    
    # Обрабатываем оплату
    success, message = await order_service.process_payment(order_id)
    
    if success:
        order = await order_service.get_order_details(order_id)
        text = "✅ <b>Заказ успешно оплачен!</b>\n\n"
        text += format_order_info(order)
        text += "\n📋 Ваш заказ передан на обработку администратору."
        
        await callback.message.edit_text(text, reply_markup=back_button())
    else:
        await callback.answer(f"❌ {message}", show_alert=True)
    
    await state.clear()
    await callback.answer()


@callback_router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession ):
    """Отменить заказ"""
    order_id = int(callback.data.split("_")[2])
    
    order_service = OrderService(session)
    success, message = await order_service.cancel_order(order_id, "Отменен пользователем")
    
    if success:
        await callback.message.edit_text(
            "❌ Заказ отменен. Средства возвращены на баланс.",
            reply_markup=back_button()
        )
    else:
        await callback.answer(f"❌ {message}", show_alert=True)
    
    await state.clear()
    await callback.answer()


@callback_router.callback_query(F.data == "cart")
async def cart_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать корзину (заказы пользователя)"""
    log_user_action(callback.from_user.id, "cart_view", "Открыл корзину")
    
    order_service = OrderService(session)
    orders = await order_service.get_user_orders(callback.from_user.id, limit=20)
    
    if not orders:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста",
            reply_markup=back_button()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "🛒 Ваша корзина:",
        reply_markup=user_orders_kb(orders)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("cart_"))
async def cart_pagination(callback: CallbackQuery, session: AsyncSession):
    """Пагинация корзины"""
    page = int(callback.data.split("_")[1])
    log_user_action(callback.from_user.id, "cart_pagination", f"Страница {page}")
    
    order_service = OrderService(session)
    orders = await order_service.get_user_orders(callback.from_user.id, limit=20)
    
    await callback.message.edit_reply_markup(
        reply_markup=user_orders_kb(orders, page)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("order_details_"))
async def order_details_callback(callback: CallbackQuery, session: AsyncSession ):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[2])
    
    order_service = OrderService(session)
    order = await order_service.get_order_details(order_id)
    
    if not order or order.user_id != callback.from_user.id:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    text = format_order_info(order, show_content=True)
    
    await callback.message.edit_text(
        text,
        reply_markup=back_button("cart")
    )
    await callback.answer()


@callback_router.callback_query(F.data == "referrals")
async def referrals_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать реферальную информацию"""
    log_user_action(callback.from_user.id, "referrals_view", "Открыл рефералы")
    
    user_service = UserService(session)
    
    from services.referral_service import ReferralService
    referral_service = ReferralService(session)
    
    stats = await referral_service.get_referral_stats(callback.from_user.id)
    
    if not stats:
        await callback.answer("❌ Данные не найдены", show_alert=True)
        return
    
    text = f"👥 <b>Реферальная программа</b>\n\n"
    text += f"🔗 Ваш код: <code>{stats['referral_code']}</code>\n"
    text += f"👥 Всего рефералов: <b>{stats['total_referrals']}</b>\n"
    text += f"🛒 Активных: <b>{stats['active_referrals']}</b>\n"
    text += f"💰 Заработано: <b>{stats['total_earnings']:.2f}₽</b>\n\n"
    
    bot_username = (await callback.bot.me()).username
    referral_link = f"https://t.me/{bot_username}?start={stats['referral_code']}"
    
    text += f"🔗 Ваша ссылка:\n<code>{referral_link}</code>\n\n"
    text += f"💡 Получайте {settings.REFERRAL_REWARD_PERCENT}% с покупок рефералов!"
    
    await callback.message.edit_text(text, reply_markup=referrals_kb())
    await callback.answer()


@callback_router.callback_query(F.data == "withdraw_funds")
async def withdraw_funds_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик вывода средств"""
    log_user_action(callback.from_user.id, "withdraw_request", "Запросил вывод средств")
    
    user_service = UserService(session)
    user_info = await user_service.get_user_info(callback.from_user.id)
    
    if not user_info:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    user = user_info["user"]
    
    text = f"💸 <b>Вывод средств</b>\n\n"
    text += f"💰 Доступно к выводу: <b>{user.referral_earnings:.2f}₽</b>\n\n"
    
    if user.referral_earnings < 100:  # Минимальная сумма для вывода
        text += f"❌ Минимальная сумма для вывода: <b>100₽</b>\n"
        text += f"💡 Приглашайте больше друзей для увеличения заработка!"
    else:
        text += f"📞 Для вывода средств обратитесь к администратору:\n"
        text += f"🔗 @{settings.SUPPORT_USERNAME}\n\n"
        text += f"📋 Укажите ваш UID: <code>{user.id}</code>"
    
    await callback.message.edit_text(text, reply_markup=back_button("referrals"))
    await callback.answer()


