from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from services import UserService, ProductService, OrderService
from keyboards import main_menu_kb, categories_kb, products_kb
from utils import format_user_info, log_user_action
from config import settings

user_router = Router()


@user_router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession):
    """Обработчик команды /start"""
    log_user_action(message.from_user.id, "start_command", "Запустил бота")
    
    user_service = UserService(session)
    
    # Проверяем реферальный код
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None
    
    # Создаем или получаем пользователя
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code or "ru"
    )
    
    # Устанавливаем реферера, если есть код
    if referral_code and not user.referrer_id:
        success = await user_service.set_referrer(user.id, referral_code)
        if success:
            await message.answer("✅ Вы успешно зарегистрированы по реферальной ссылке!")
    
    # Проверяем, является ли пользователь админом
    if message.from_user.id in settings.ADMIN_IDS:
        from keyboards.inline_keyboards import admin_menu_kb
        welcome_text = f"👋 Добро пожаловать, {user.first_name or 'админ'}!\n\n"
        welcome_text += "⚙️ <b>Админ-панель</b>\n"
        welcome_text += "Используйте меню ниже для управления ботом:"
        
        await message.answer(welcome_text, reply_markup=admin_menu_kb())
    else:
        welcome_text = f"👋 Добро пожаловать, {user.first_name or 'друг'}!\n\n"
        welcome_text += "🛍 Это бот для покупки цифровых товаров.\n"
        welcome_text += "Выберите действие из меню ниже:"
        
        await message.answer(welcome_text, reply_markup=main_menu_kb())


@user_router.message(Command("menu"))
async def menu_handler(message: Message):
    """Обработчик команды /menu"""
    await message.answer("📋 Главное меню:", reply_markup=main_menu_kb())


@user_router.message(Command("profile"))
async def profile_handler(message: Message, session: AsyncSession):
    """Обработчик команды /profile"""
    log_user_action(message.from_user.id, "profile_command", "Вызвал команду /profile")
    
    user_service = UserService(session)
    
    user_info = await user_service.get_user_info(message.from_user.id)
    if not user_info:
        await message.answer("❌ Пользователь не найден")
        return
    
    text = format_user_info(
        user_info["user"],
        user_info["referrals_count"]
    )
    
    await message.answer(text, reply_markup=main_menu_kb())


@user_router.message(Command("help"))
async def help_handler(message: Message):
    """Обработчик команды /help"""
    help_text = """
🤖 <b>Помощь по боту</b>

<b>Основные команды:</b>
/start - Запуск бота
/menu - Главное меню
/profile - Ваш профиль
/help - Эта справка

<b>Как купить товар:</b>
1️⃣ Выберите "🛍 Каталог" в меню
2️⃣ Выберите категорию товаров
3️⃣ Выберите нужный товар
4️⃣ Нажмите "🛒 Купить"
5️⃣ Подтвердите заказ

<b>Пополнение баланса:</b>
Используйте кнопку "💰 Пополнить баланс" в главном меню

<b>Реферальная программа:</b>
Приглашайте друзей и получайте {:.1f}% с их покупок!

❓ Если у вас есть вопросы, обратитесь к администратору.
    """.format(settings.REFERRAL_REWARD_PERCENT)
    
    await message.answer(help_text)


@user_router.message(F.text.contains("поиск") | F.text.contains("найти"))
async def search_prompt(message: Message):
    """Подсказка для поиска"""
    await message.answer(
        "🔍 Для поиска товаров используйте кнопку 'Поиск' в главном меню\n"
        "или отправьте сообщение в формате: найти <название товара>"
    )


@user_router.message(F.text.startswith("найти "))
async def search_handler(message: Message, session: AsyncSession):
    """Обработчик поиска товаров"""
    query = message.text[6:].strip()  # Убираем "найти "
    log_user_action(message.from_user.id, "search_query", f"Поиск: {query}")
    
    if len(query) < 2:
        await message.answer("❌ Запрос слишком короткий. Минимум 2 символа.")
        return
    
    product_service = ProductService(session)
    products = await product_service.search_products(query)
    
    if not products:
        await message.answer(f"❌ По запросу '{query}' ничего не найдено.")
        return
    
    text = f"🔍 Результаты поиска по запросу '{query}':\n\n"
    
    for product in products[:10]:  # Показываем первые 10 результатов
        availability = "✅" if (product.is_unlimited or product.stock_quantity > 0) else "❌"
        text += f"{availability} <b>{product.name}</b> - {product.price:.2f}₽\n"
        text += f"📂 {product.category.name}\n\n"
    
    if len(products) > 10:
        text += f"... и еще {len(products) - 10} товаров\n\n"
    
    text += "Используйте каталог для покупки товаров."
    
    await message.answer(text, reply_markup=main_menu_kb())