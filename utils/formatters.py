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
        text += f"💰 Общий баланс: <b>{stats['total_balance']:.2f}₽</b>\n\n"
    
    if "total_orders" in stats:
        text += f"📦 Всего заказов: <b>{stats['total_orders']}</b>\n"
        text += f"📈 За {stats['days']} дней: <b>{stats['period_orders']}</b>\n"
        text += f"💸 Выручка за период: <b>{stats['period_revenue']:.2f}₽</b>\n\n"
        
        text += f"🕐 Ожидают: <b>{stats['pending_orders']}</b>\n"
        text += f"💳 Оплачены: <b>{stats['paid_orders']}</b>\n"
        text += f"✅ Выданы: <b>{stats['delivered_orders']}</b>\n"
    
    return text