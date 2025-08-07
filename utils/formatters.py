from datetime import datetime
from database.models import User, Product, Order, OrderStatus


def format_user_info(user: User, referrals_count: int = 0) -> str:
    """Форматировать информацию о пользователе для профиля"""
    name = user.first_name or "Пользователь"
    if user.last_name:
        name += f" {user.last_name}"
    
    text = f"👤 <b>{name}</b>\n"
    if user.username:
        text += f"🔗 @{user.username}\n"
    
    text += f"\n🆔 UID: <code>{user.id}</code>\n"
    text += f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
    text += f"📦 Заказов: <b>{user.total_orders}</b>\n"
    text += f"💸 Потрачено: <b>{user.total_spent:.2f}₽</b>\n"
    
    # Промокод пользователя
    if user.promo_code:
        text += f"\n🎟 Ваш промокод: <code>{user.promo_code}</code>\n"
        text += f"💡 <i>Используйте промокод для получения скидок и заработка!</i>\n"
    
    return text


def format_product_info(product: Product, show_stock: bool = False) -> str:
    """Форматировать информацию о товаре"""
    text = f"🛍 <b>{product.name}</b>\n"
    
    if product.description:
        text += f"\n📝 {product.description}\n"
    
    text += f"\n💰 Цена: <b>{product.price:.2f}₽</b>\n"
    text += f"📂 Категория: <b>{product.category.name}</b>\n"
    
    if show_stock:
        if product.is_unlimited:
            text += f"📦 В наличии: <b>∞</b>\n"
        else:
            text += f"📦 В наличии: <b>{product.stock_quantity}</b>\n"
        
        text += f"📊 Продано: <b>{product.total_sold}</b>\n"
    else:
        # Для покупателей показываем только доступность
        if product.is_unlimited or product.stock_quantity > 0:
            text += f"✅ <b>В наличии</b>\n"
        else:
            text += f"❌ <b>Нет в наличии</b>\n"
    
    return text


def format_order_info(order: Order, show_content: bool = False) -> str:
    """Форматировать информацию о заказе"""
    status_icons = {
        OrderStatus.PENDING.value: "🕐",
        OrderStatus.PAID.value: "💳", 
        OrderStatus.DELIVERED.value: "✅",
        OrderStatus.CANCELLED.value: "❌"
    }
    
    status_names = {
        OrderStatus.PENDING.value: "Ожидает оплаты",
        OrderStatus.PAID.value: "Оплачен",
        OrderStatus.DELIVERED.value: "Выдан", 
        OrderStatus.CANCELLED.value: "Отменен"
    }
    
    icon = status_icons.get(order.status, "❓")
    status_name = status_names.get(order.status, "Неизвестно")
    
    text = f"{icon} <b>Заказ #{order.id}</b>\n"
    text += f"📦 Товар: <b>{order.product.name}</b>\n"
    text += f"📊 Количество: <b>{order.quantity}</b>\n"
    text += f"💰 Сумма: <b>{order.total_price:.2f}₽</b>\n"
    text += f"📅 Статус: <b>{status_name}</b>\n"
    text += f"🕐 Создан: <b>{order.created_at.strftime('%d.%m.%Y %H:%M')}</b>\n"
    
    if order.delivered_at:
        text += f"✅ Выдан: <b>{order.delivered_at.strftime('%d.%m.%Y %H:%M')}</b>\n"
    
    if show_content and order.delivered_content:
        text += f"\n📋 <b>Содержимое заказа:</b>\n"
        text += f"<code>{order.delivered_content}</code>\n"
    
    if order.notes:
        text += f"\n📝 Примечания: <i>{order.notes}</i>\n"
    
    return text


def format_stats(stats: dict) -> str:
    """Форматировать статистику"""
    text = "📊 <b>Статистика</b>\n\n"
    
    if "total_users" in stats:
        text += f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        text += f"🛒 Активных покупателей: <b>{stats['active_users']}</b>\n"
    
    if "total_orders" in stats:
        text += f"📦 Всего заказов: <b>{stats['total_orders']}</b>\n"
    
    if "total_revenue" in stats:
        text += f"💰 Общая выручка: <b>{stats['total_revenue']:.2f}₽</b>\n"
    
    return text


def format_user_brief_info(user_info: dict) -> str:
    """Форматировать краткую информацию о пользователе для выдачи товара"""
    user = user_info["user"]
    total_orders = user_info["total_orders"]
    total_spent = user_info["total_spent"]
    recent_orders = user_info["recent_orders"]
    
    # Формируем имя пользователя
    name = user.first_name or "Пользователь"
    if user.last_name:
        name += f" {user.last_name}"
    
    text = f"👤 <b>{name}</b>\n"
    if user.username:
        text += f"🔗 @{user.username}\n"
    
    text += f"🆔 UID: <code>{user.id}</code>\n"
    text += f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
    text += f"📦 Заказов: <b>{total_orders}</b>\n"
    text += f"💸 Потрачено: <b>{total_spent:.2f}₽</b>\n"
    
    # Уровень активности
    if user_info["is_vip_buyer"]:
        activity_level = "🟢 VIP"
    elif user_info["is_regular_buyer"]:
        activity_level = "🟡 Регулярный"
    elif user_info["is_active_buyer"]:
        activity_level = "🟠 Активный"
    else:
        activity_level = "⚪ Новый"
    
    text += f"📊 Уровень: {activity_level}\n"
    
    # Последние заказы
    if recent_orders:
        text += f"\n📋 <b>Последние заказы:</b>\n"
        for order in recent_orders[:3]:
            status_icon = {
                "pending": "🕐",
                "paid": "💳",
                "delivered": "✅",
                "cancelled": "❌"
            }.get(order.status, "❓")
            
            text += f"{status_icon} {order.product.name} - {order.total_price:.2f}₽ ({order.created_at.strftime('%d.%m')})\n"
    
    return text


def format_user_search_result(user: dict) -> str:
    """Форматировать результат поиска пользователя"""
    text = f"🔍 <b>Результат поиска:</b>\n\n"
    
    name = user.first_name or "Пользователь"
    if user.last_name:
        name += f" {user.last_name}"
    
    text += f"👤 <b>{name}</b>\n"
    if user.username:
        text += f"🔗 @{user.username}\n"
    
    text += f"🆔 UID: <code>{user.id}</code>\n"
    text += f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
    text += f"📦 Заказов: <b>{user.total_orders}</b>\n"
    text += f"💸 Потрачено: <b>{user.total_spent:.2f}₽</b>\n"
    
    # Промокод пользователя
    if user.promo_code:
        text += f"🎟 Промокод: <code>{user.promo_code}</code>\n"
    
    # Реферальный код
    if user.referral_code:
        text += f"👥 Реферальный код: <code>{user.referral_code}</code>\n"
    
    return text


def format_user_orders_summary(summary: dict) -> str:
    """Форматировать сводку заказов пользователя"""
    if not summary["user_found"]:
        return "❌ Пользователь не найден"
    
    user = summary["user"]
    name = user.first_name or "Пользователь"
    if user.last_name:
        name += f" {user.last_name}"
    
    text = f"📊 <b>Сводка заказов: {name}</b>\n\n"
    
    text += f"📦 Всего заказов: <b>{summary['total_orders']}</b>\n"
    text += f"🕐 Ожидают оплаты: <b>{summary['pending_orders']}</b>\n"
    text += f"💳 Оплачены: <b>{summary['paid_orders']}</b>\n"
    text += f"✅ Выданы: <b>{summary['delivered_orders']}</b>\n"
    text += f"❌ Отменены: <b>{summary['cancelled_orders']}</b>\n"
    text += f"💸 Потрачено: <b>{summary['total_spent']:.2f}₽</b>\n"
    
    # Последние заказы
    if summary["recent_orders"]:
        text += f"\n📋 <b>Последние заказы:</b>\n"
        for order in summary["recent_orders"][:3]:
            status_icon = {
                "pending": "🕐",
                "paid": "💳",
                "delivered": "✅",
                "cancelled": "❌"
            }.get(order.status, "❓")
            
            text += f"{status_icon} {order.product.name} - {order.total_price:.2f}₽ ({order.created_at.strftime('%d.%m %H:%M')})\n"
    
    return text


def format_user_trust_score(trust_info: dict) -> str:
    """Форматировать оценку доверия к пользователю"""
    score = trust_info["score"]
    level = trust_info["level"]
    factors = trust_info["factors"]
    
    # Иконки уровней доверия
    level_icons = {
        "high": "🟢",
        "medium": "🟡", 
        "low": "🟠",
        "new": "⚪",
        "unknown": "❓"
    }
    
    level_names = {
        "high": "Высокое",
        "medium": "Среднее",
        "low": "Низкое", 
        "new": "Новый",
        "unknown": "Неизвестно"
    }
    
    icon = level_icons.get(level, "❓")
    level_name = level_names.get(level, "Неизвестно")
    
    text = f"🔒 <b>Оценка доверия</b>\n\n"
    text += f"📊 Оценка: <b>{score}/100</b>\n"
    text += f"🎯 Уровень: {icon} <b>{level_name}</b>\n\n"
    
    if factors:
        text += f"📋 <b>Факторы:</b>\n"
        for factor in factors:
            text += f"• {factor}\n"
    
    # Дополнительная статистика
    text += f"\n📊 <b>Статистика:</b>\n"
    text += f"• Заказов: <b>{trust_info['total_orders']}</b>\n"
    text += f"• Успешных: <b>{trust_info['successful_orders']}</b>\n"
    text += f"• Отмененных: <b>{trust_info['cancelled_orders']}</b>\n"
    text += f"• Возраст аккаунта: <b>{trust_info['account_age_days']}</b> дней\n"
    
    return text


def format_user_activity_level(activity_level: str) -> str:
    """Форматировать уровень активности пользователя"""
    level_icons = {
        "new": "⚪",
        "occasional": "🟠", 
        "regular": "🟡",
        "active": "🟢",
        "vip": "💎",
        "unknown": "❓"
    }
    
    level_names = {
        "new": "Новый пользователь",
        "occasional": "Случайный покупатель",
        "regular": "Регулярный покупатель", 
        "active": "Активный покупатель",
        "vip": "VIP клиент",
        "unknown": "Неизвестно"
    }
    
    icon = level_icons.get(activity_level, "❓")
    name = level_names.get(activity_level, "Неизвестно")
    
    return f"{icon} <b>{name}</b>"


def format_user_for_delivery(user_info: dict) -> str:
    """Форматировать информацию о пользователе для выдачи товара"""
    user = user_info["user"]
    total_orders = user_info["total_orders"]
    total_spent = user_info["total_spent"]
    
    # Формируем имя пользователя
    name = user.first_name or "Пользователь"
    if user.last_name:
        name += f" {user.last_name}"
    
    text = f"🎯 <b>Выдача товара пользователю:</b>\n\n"
    text += f"👤 <b>{name}</b>\n"
    if user.username:
        text += f"🔗 @{user.username}\n"
    
    text += f"🆔 UID: <code>{user.id}</code>\n"
    text += f"💰 Баланс: <b>{user.balance:.2f}₽</b>\n"
    text += f"📦 Заказов: <b>{total_orders}</b>\n"
    text += f"💸 Потрачено: <b>{total_spent:.2f}₽</b>\n"
    
    # Уровень активности
    if user_info["is_vip_buyer"]:
        activity_level = "💎 VIP клиент"
    elif user_info["is_regular_buyer"]:
        activity_level = "🟡 Регулярный клиент"
    elif user_info["is_active_buyer"]:
        activity_level = "🟢 Активный клиент"
    else:
        activity_level = "⚪ Новый клиент"
    
    text += f"📊 Статус: {activity_level}\n"
    
    # Промокод для скидок
    if user.promo_code:
        text += f"🎟 Промокод: <code>{user.promo_code}</code>\n"
    
    return text


def format_delivery_message(order: dict, product: dict, user: dict, admin_info: dict = None) -> str:
    """Форматировать красивое сообщение о выдаче товара пользователю"""
    
    # Заголовок с эмодзи
    text = "🎉 <b>ТОВАР ВЫДАН!</b>\n\n"
    
    # Информация о заказе
    text += "📋 <b>Информация о заказе:</b>\n"
    text += f"🆔 Заказ: <code>#{order['id']}</code>\n"
    text += f"📅 Дата: <b>{order['created_at']}</b>\n"
    text += f"💰 Сумма: <b>{order['total_price']:.2f}₽</b>\n"
    text += f"📦 Количество: <b>{order['quantity']}</b>\n\n"
    
    # Информация о товаре
    text += "🛍 <b>Товар:</b>\n"
    text += f"📦 Название: <b>{product['name']}</b>\n"
    text += f"📂 Категория: <b>{product['category_name']}</b>\n"
    text += f"💰 Цена: <b>{product['price']:.2f}₽</b>\n"
    
    if product.get('duration'):
        text += f"⏱ Длительность: <b>{product['duration']}</b>\n"
    
    if product.get('product_type'):
        type_names = {
            "account": "👤 Аккаунт",
            "key": "🔑 Ключ активации", 
            "promo": "🎫 Промокод"
        }
        type_name = type_names.get(product['product_type'], product['product_type'])
        text += f"📋 Тип: <b>{type_name}</b>\n"
    
    text += "\n"
    
    # Информация о пользователе
    name = user.get('first_name', 'Пользователь')
    if user.get('last_name'):
        name += f" {user['last_name']}"
    
    text += "👤 <b>Получатель:</b>\n"
    text += f"👤 Имя: <b>{name}</b>\n"
    if user.get('username'):
        text += f"🔗 Username: @{user['username']}\n"
    text += f"🆔 ID: <code>{user['id']}</code>\n"
    text += f"💰 Баланс: <b>{user.get('balance', 0):.2f}₽</b>\n"
    text += f"📦 Заказов: <b>{user.get('total_orders', 0)}</b>\n\n"
    
    # Информация о выдаче
    text += "✅ <b>Выдача:</b>\n"
    text += f"🕐 Время выдачи: <b>{order.get('delivered_at', 'Сейчас')}</b>\n"
    
    if admin_info:
        admin_name = admin_info.get('first_name', 'Администратор')
        if admin_info.get('last_name'):
            admin_name += f" {admin_info['last_name']}"
        text += f"👨‍💼 Выдал: <b>{admin_name}</b>\n"
        if admin_info.get('username'):
            text += f"🔗 @{admin_info['username']}\n"
    
    return text


def format_delivery_content_message(order: dict, product: dict, content: str, include_manual: bool = True) -> str:
    """Форматировать сообщение с содержимым выданного товара"""
    
    text = "🎁 <b>ВАШ ТОВАР ГОТОВ!</b>\n\n"
    
    # Информация о заказе
    text += "📋 <b>Детали заказа:</b>\n"
    text += f"🆔 Заказ: <code>#{order['id']}</code>\n"
    text += f"📦 Товар: <b>{product['name']}</b>\n"
    text += f"💰 Сумма: <b>{order['total_price']:.2f}₽</b>\n"
    text += f"📅 Дата: <b>{order['created_at']}</b>\n\n"
    
    # Содержимое товара
    text += "📦 <b>СОДЕРЖИМОЕ ТОВАРА:</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"<code>{content}</code>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Предупреждения
    text += "⚠️ <b>ВАЖНО:</b>\n"
    text += "• Сохраните содержимое в надежном месте\n"
    text += "• Не передавайте данные третьим лицам\n"
    text += "• При проблемах обращайтесь в поддержку\n\n"
    
    # Добавляем мануал если есть
    if include_manual and product.get('category_manual_url'):
        text += "📖 <b>Инструкция по использованию:</b>\n"
        text += f"🔗 <a href='{product['category_manual_url']}'>Открыть мануал</a>\n\n"
    
    # Контакты поддержки
    from config import settings
    if hasattr(settings, 'SUPPORT_USERNAME') and settings.SUPPORT_USERNAME:
        text += "🆘 <b>Поддержка:</b>\n"
        text += f"💬 @{settings.SUPPORT_USERNAME}\n\n"
    
    # Благодарность
    text += "🙏 <b>Спасибо за покупку!</b>\n"
    text += "💡 Рекомендуем нас друзьям\n"
    text += "⭐ Оставьте отзыв о нашем сервисе"
    
    return text


def format_delivery_admin_notification(order: dict, product: dict, user: dict, admin_info: dict) -> str:
    """Форматировать уведомление администратору о выданном товаре"""
    
    text = "✅ <b>ТОВАР УСПЕШНО ВЫДАН</b>\n\n"
    
    # Информация о заказе
    text += "📋 <b>Детали выдачи:</b>\n"
    text += f"🆔 Заказ: <code>#{order['id']}</code>\n"
    text += f"📦 Товар: <b>{product['name']}</b>\n"
    text += f"💰 Сумма: <b>{order['total_price']:.2f}₽</b>\n"
    text += f"📅 Дата выдачи: <b>{order.get('delivered_at', 'Сейчас')}</b>\n\n"
    
    # Информация о пользователе
    name = user.get('first_name', 'Пользователь')
    if user.get('last_name'):
        name += f" {user['last_name']}"
    
    text += "👤 <b>Получатель:</b>\n"
    text += f"👤 Имя: <b>{name}</b>\n"
    if user.get('username'):
        text += f"🔗 @{user['username']}\n"
    text += f"🆔 ID: <code>{user['id']}</code>\n"
    text += f"📦 Заказов: <b>{user.get('total_orders', 0)}</b>\n"
    text += f"💸 Потрачено: <b>{user.get('total_spent', 0):.2f}₽</b>\n\n"
    
    # Информация о выдаче
    admin_name = admin_info.get('first_name', 'Администратор')
    if admin_info.get('last_name'):
        admin_name += f" {admin_info['last_name']}"
    
    text += "👨‍💼 <b>Выдал:</b>\n"
    text += f"👤 Имя: <b>{admin_name}</b>\n"
    if admin_info.get('username'):
        text += f"🔗 @{admin_info['username']}\n"
    text += f"🆔 ID: <code>{admin_info['id']}</code>\n\n"
    
    # Статистика
    text += "📊 <b>Статистика:</b>\n"
    text += f"📦 Всего выдано товаров: <b>{order.get('total_delivered', 0)}</b>\n"
    text += f"💰 Общая выручка: <b>{order.get('total_revenue', 0):.2f}₽</b>\n"
    
    return text


def format_delivery_error_message(error_type: str, order_id: int = None, product_name: str = None) -> str:
    """Форматировать сообщение об ошибке при выдаче товара"""
    
    text = "❌ <b>ОШИБКА ПРИ ВЫДАЧЕ ТОВАРА</b>\n\n"
    
    if order_id:
        text += f"🆔 Заказ: <code>#{order_id}</code>\n"
    
    if product_name:
        text += f"📦 Товар: <b>{product_name}</b>\n\n"
    
    # Типы ошибок
    error_messages = {
        "order_not_found": "❌ Заказ не найден в базе данных",
        "product_not_found": "❌ Товар не найден в базе данных", 
        "user_not_found": "❌ Пользователь не найден в базе данных",
        "order_already_delivered": "❌ Заказ уже был выдан ранее",
        "order_cancelled": "❌ Заказ был отменен",
        "insufficient_balance": "❌ Недостаточно средств у пользователя",
        "product_out_of_stock": "❌ Товар закончился на складе",
        "delivery_failed": "❌ Ошибка при отправке сообщения пользователю",
        "database_error": "❌ Ошибка базы данных",
        "unknown_error": "❌ Неизвестная ошибка"
    }
    
    error_msg = error_messages.get(error_type, "❌ Произошла ошибка")
    text += f"🔍 <b>Причина:</b> {error_msg}\n\n"
    
    text += "💡 <b>Рекомендации:</b>\n"
    text += "• Проверьте правильность данных заказа\n"
    text += "• Убедитесь, что товар в наличии\n"
    text += "• Проверьте баланс пользователя\n"
    text += "• Обратитесь к технической поддержке\n\n"
    
    text += "🆘 <b>Поддержка:</b>\n"
    from config import settings
    if hasattr(settings, 'SUPPORT_USERNAME') and settings.SUPPORT_USERNAME:
        text += f"💬 @{settings.SUPPORT_USERNAME}"
    
    return text


def format_delivery_confirmation_message(order: dict, product: dict, user: dict) -> str:
    """Форматировать сообщение подтверждения выдачи товара"""
    
    text = "🤔 <b>ПОДТВЕРЖДЕНИЕ ВЫДАЧИ ТОВАРА</b>\n\n"
    
    # Информация о заказе
    text += "📋 <b>Детали заказа:</b>\n"
    text += f"🆔 Заказ: <code>#{order['id']}</code>\n"
    text += f"📦 Товар: <b>{product['name']}</b>\n"
    text += f"💰 Сумма: <b>{order['total_price']:.2f}₽</b>\n"
    text += f"📅 Дата заказа: <b>{order['created_at']}</b>\n\n"
    
    # Информация о пользователе
    name = user.get('first_name', 'Пользователь')
    if user.get('last_name'):
        name += f" {user['last_name']}"
    
    text += "👤 <b>Получатель:</b>\n"
    text += f"👤 Имя: <b>{name}</b>\n"
    if user.get('username'):
        text += f"🔗 @{user['username']}\n"
    text += f"🆔 ID: <code>{user['id']}</code>\n"
    text += f"💰 Баланс: <b>{user.get('balance', 0):.2f}₽</b>\n"
    text += f"📦 Заказов: <b>{user.get('total_orders', 0)}</b>\n\n"
    
    text += "⚠️ <b>ВНИМАНИЕ:</b>\n"
    text += "• Убедитесь, что данные пользователя верны\n"
    text += "• Проверьте, что товар соответствует заказу\n"
    text += "• Подтвердите выдачу только после проверки\n\n"
    
    text += "✅ <b>Для подтверждения нажмите кнопку ниже</b>"
    
    return text


def format_delivery_success_stats(stats: dict) -> str:
    """Форматировать статистику успешных выдач"""
    
    text = "📊 <b>СТАТИСТИКА ВЫДАЧ</b>\n\n"
    
    text += "📈 <b>Сегодня:</b>\n"
    text += f"✅ Выдано: <b>{stats.get('today_delivered', 0)}</b>\n"
    text += f"💰 Выручка: <b>{stats.get('today_revenue', 0):.2f}₽</b>\n"
    text += f"👥 Покупателей: <b>{stats.get('today_customers', 0)}</b>\n\n"
    
    text += "📈 <b>За неделю:</b>\n"
    text += f"✅ Выдано: <b>{stats.get('week_delivered', 0)}</b>\n"
    text += f"💰 Выручка: <b>{stats.get('week_revenue', 0):.2f}₽</b>\n"
    text += f"👥 Покупателей: <b>{stats.get('week_customers', 0)}</b>\n\n"
    
    text += "📈 <b>За месяц:</b>\n"
    text += f"✅ Выдано: <b>{stats.get('month_delivered', 0)}</b>\n"
    text += f"💰 Выручка: <b>{stats.get('month_revenue', 0):.2f}₽</b>\n"
    text += f"👥 Покупателей: <b>{stats.get('month_customers', 0)}</b>\n\n"
    
    # Топ товаров
    if stats.get('top_products'):
        text += "🏆 <b>Топ товаров:</b>\n"
        for i, product in enumerate(stats['top_products'][:5], 1):
            text += f"{i}. {product['name']} - {product['count']} шт.\n"
    
    return text


def format_manual_url(category_name: str, manual_url: str = None) -> str:
    """Форматировать ссылку на мануал"""
    if not manual_url:
        return ""
    
    text = "\n📖 <b>Инструкция по использованию:</b>\n"
    text += f"🔗 <a href='{manual_url}'>Открыть мануал для {category_name}</a>\n"
    
    return text


def format_delivery_footer() -> str:
    """Форматировать подвал сообщения о выдаче"""
    from config import settings
    
    text = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += "💡 <b>Полезные ссылки:</b>\n"
    text += "🛍 <a href='https://t.me/your_bot'>Каталог товаров</a>\n"
    text += "📞 <a href='https://t.me/your_support'>Поддержка</a>\n"
    text += "📖 <a href='https://t.me/your_help'>Помощь</a>\n\n"
    
    # Промокод для следующей покупки
    text += "🎟 <b>Промокод для скидки:</b>\n"
    text += "💎 <code>THANKS10</code> - скидка 10%\n\n"
    
    text += "⭐ <b>Оцените наш сервис!</b>\n"
    text += "🙏 Спасибо за покупку!"
    
    return text