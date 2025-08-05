"""Шаблоны сообщений для склада товаров"""

from database.models import Product, ProductType


class WarehouseMessages:
    """Класс с шаблонами сообщений для склада"""
    
    # Добавление товара
    ADD_PRODUCT_START = (
        "➕ <b>Добавление товара на склад</b>\n\n"
        "Пройдем пошаговый мастер добавления нового товара.\n\n"
        "Шаг 1/7: Выберите категорию для товара:"
    )
    
    ADD_PRODUCT_NAME = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 2/7: Введите название товара:\n\n"
        "Например: <code>Netflix Premium 1 месяц</code>"
    )
    
    ADD_PRODUCT_TYPE = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 3/7: Выберите тип товара:"
    )
    
    ADD_PRODUCT_DURATION = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 4/7: Введите длительность товара:\n\n"
        "Примеры: <code>1 месяц</code>, <code>12 месяцев</code>, <code>lifetime</code>, <code>разовая активация</code>"
    )
    
    ADD_PRODUCT_CONTENT_ACCOUNT = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 5/7: Введите данные аккаунта в формате:\n\n"
        "<code>логин:пароль</code>\n\n"
        "Например: <code>user@example.com:password123</code>"
    )
    
    ADD_PRODUCT_CONTENT_KEY = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 5/7: Введите ключ активации:\n\n"
        "Например: <code>XXXX-XXXX-XXXX-XXXX</code>"
    )
    
    ADD_PRODUCT_CONTENT_PROMO = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 5/7: Введите промокод:\n\n"
        "Например: <code>SAVE20OFF</code>"
    )
    
    ADD_PRODUCT_PRICE = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 6/7: Введите цену товара в рублях:\n\n"
        "Например: <code>299</code> или <code>99.99</code>"
    )
    
    ADD_PRODUCT_CONFIRMATION = (
        "➕ <b>Подтверждение добавления товара</b>\n\n"
        "📋 <b>Данные товара:</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "📂 <b>Категория:</b> {category}\n"
        "🔖 <b>Тип:</b> {product_type}\n"
        "⏰ <b>Длительность:</b> {duration}\n"
        "💰 <b>Цена:</b> {price:.2f}₽\n"
        "📦 <b>Содержимое:</b> {content_preview}\n\n"
        "❓ Сохранить товар?"
    )
    
    ADD_PRODUCT_SUCCESS = (
        "✅ <b>Товар успешно добавлен!</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "🆔 <b>ID:</b> #{id}\n"
        "💰 <b>Цена:</b> {price:.2f}₽\n"
        "📦 <b>Остаток:</b> 1 шт.\n\n"
        "Товар добавлен в каталог и доступен для заказа."
    )
    
    # Выдача товара
    GIVE_PRODUCT_START = (
        "🎯 <b>Выдача товара</b>\n\n"
        "Выберите товар для выдачи (доступны только товары с остатком > 0):"
    )
    
    GIVE_PRODUCT_USER = (
        "🎯 <b>Выдача товара</b>\n\n"
        "📦 <b>Товар:</b> {product_name}\n"
        "💰 <b>Цена:</b> {price:.2f}₽\n"
        "📊 <b>Остаток:</b> {stock} шт.\n\n"
        "👤 Введите username пользователя (без @) или его Telegram ID:"
    )
    
    GIVE_PRODUCT_CONFIRMATION = (
        "🎯 <b>Подтверждение выдачи товара</b>\n\n"
        "📦 <b>Товар:</b> {product_name}\n"
        "💰 <b>Цена:</b> {price:.2f}₽\n"
        "👤 <b>Получатель:</b> {recipient}\n"
        "📦 <b>Содержимое:</b> <code>{content}</code>\n\n"
        "❓ Выдать товар пользователю?"
    )
    
    GIVE_PRODUCT_SUCCESS = (
        "✅ <b>Товар успешно выдан!</b>\n\n"
        "📦 <b>Товар:</b> {product_name}\n"
        "👤 <b>Получатель:</b> {recipient}\n"
        "📊 <b>Новый остаток:</b> {new_stock} шт.\n\n"
        "Пользователю отправлено уведомление с товаром."
    )
    
    GIVE_PRODUCT_USER_NOTIFICATION = (
        "🎁 <b>Вам выдан товар!</b>\n\n"
        "📦 <b>Товар:</b> {product_name}\n"
        "🔖 <b>Тип:</b> {product_type_display}\n"
        "⏰ <b>Длительность:</b> {duration}\n\n"
        "📋 <b>Данные для использования:</b>\n"
        "<code>{content}</code>\n\n"
        "💡 <i>Сохраните эти данные в надежном месте</i>"
    )
    
    # Ошибки
    ERROR_PRODUCT_NOT_FOUND = "❌ Товар не найден или удален"
    ERROR_NO_STOCK = "❌ Товар закончился на складе"
    ERROR_USER_NOT_FOUND = "❌ Пользователь не найден. Убедитесь, что пользователь запускал бота"
    ERROR_INVALID_PRICE = "❌ Неверный формат цены. Введите число (например: 299 или 99.99)"
    ERROR_INVALID_CONTENT_FORMAT = "❌ Неверный формат данных. Следуйте указанному примеру"
    ERROR_CATEGORY_NOT_FOUND = "❌ Категория не найдена"
    ERROR_ACCESS_DENIED = "❌ У вас нет прав доступа к этой функции"
    
    # Кнопки
    BUTTON_ACCOUNT = "👤 Аккаунт (логин/пароль)"
    BUTTON_KEY = "🔑 Ключ активации"
    BUTTON_PROMO = "🎫 Промокод"
    BUTTON_SAVE = "💾 Сохранить"
    BUTTON_CANCEL = "❌ Отмена"
    BUTTON_GIVE = "🎯 Выдать"
    BUTTON_BACK = "🔙 Назад"
    
    @staticmethod
    def get_product_type_display(product_type: str) -> str:
        """Получить отображаемое название типа товара"""
        type_map = {
            ProductType.ACCOUNT.value: "👤 Аккаунт",
            ProductType.KEY.value: "🔑 Ключ активации", 
            ProductType.PROMO.value: "🎫 Промокод"
        }
        return type_map.get(product_type, "❓ Неизвестный тип")
    
    @staticmethod
    def get_content_preview(content: str, product_type: str) -> str:
        """Получить превью содержимого товара для подтверждения"""
        if not content:
            return "Не указано"
        
        if product_type == ProductType.ACCOUNT.value:
            # Для аккаунтов показываем только логин
            parts = content.split(":")
            if len(parts) >= 2:
                return f"{parts[0]}:***"
            return content[:20] + "..." if len(content) > 20 else content
        else:
            # Для ключей и промокодов показываем частично
            if len(content) > 20:
                return content[:10] + "..." + content[-5:]
            return content