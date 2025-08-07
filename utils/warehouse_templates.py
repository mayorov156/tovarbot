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
    
    MANUAL_NOTIFICATION = (
        "📚 <b>Мануал/Инструкция</b>\n\n"
        "Для товара <b>{product_name}</b> доступна инструкция:\n\n"
        "🔗 {manual_url}\n\n"
        "💡 <i>Рекомендуем ознакомиться с инструкцией перед использованием</i>"
    )
    
    # Создание категории
    CREATE_CATEGORY_START = (
        "📂 <b>Создание новой категории</b>\n\n"
        "Шаг 1/3: Введите название категории:\n\n"
        "Например: <code>Стриминговые сервисы</code>"
    )
    
    CREATE_CATEGORY_DESCRIPTION = (
        "📂 <b>Создание категории</b>\n\n"
        "Шаг 2/3: Введите описание категории (необязательно):\n\n"
        "Например: <code>Подписки на Netflix, Spotify и другие сервисы</code>\n\n"
        "Или отправьте <code>-</code> чтобы пропустить"
    )
    

    
    CREATE_CATEGORY_CONFIRMATION = (
        "📂 <b>Подтверждение создания категории</b>\n\n"
        "📋 <b>Данные категории:</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "📝 <b>Описание:</b> {description}\n\n"
        "❓ Создать категорию?"
    )
    
    CREATE_CATEGORY_SUCCESS = (
        "✅ <b>Категория успешно создана!</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "🆔 <b>ID:</b> #{id}\n"
        "📝 <b>Описание:</b> {description}\n\n"
        "💡 <i>Инструкция для всех товаров настраивается в системных настройках</i>\n\n"
        "Теперь вы можете добавлять товары в эту категорию."
    )
    
    # Массовое добавление товаров
    MASS_ADD_START = (
        "📦 <b>Массовое добавление товаров</b>\n\n"
        "Шаг 1/6: Выберите категорию для товаров:"
    )
    
    MASS_ADD_NAME = (
        "📦 <b>Массовое добавление товаров</b>\n\n"
        "Шаг 2/6: Введите базовое название товара:\n\n"
        "Например: <code>Netflix Premium</code>\n"
        "Товары будут пронумерованы автоматически."
    )
    
    MASS_ADD_TYPE = (
        "📦 <b>Массовое добавление товаров</b>\n\n"
        "Шаг 3/6: Выберите тип товара:"
    )
    
    MASS_ADD_DURATION = (
        "📦 <b>Массовое добавление товаров</b>\n\n"
        "Шаг 4/6: Введите длительность подписки:\n\n"
        "Примеры: <code>1 месяц</code>, <code>6 месяцев</code>, <code>1 год</code>, <code>lifetime</code>"
    )
    
    MASS_ADD_PRICE = (
        "📦 <b>Массовое добавление товаров</b>\n\n"
        "Шаг 5/6: Введите цену за единицу товара:\n\n"
        "Например: <code>299</code> или <code>99.99</code>"
    )
    
    MASS_ADD_CONTENT = (
        "📦 <b>Массовое добавление товаров</b>\n\n"
        "Шаг 6/6: Введите содержимое товаров:\n\n"
        "{content_format}\n\n"
        "Каждая строка = один товар. Пустые строки игнорируются."
    )
    
    MASS_ADD_CONFIRMATION = (
        "📦 <b>Подтверждение массового добавления</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "📂 <b>Категория:</b> {category}\n"
        "📦 <b>Тип:</b> {product_type}\n"
        "⏱ <b>Длительность:</b> {duration}\n"
        "💰 <b>Цена:</b> {price}₽\n"
        "📊 <b>Количество:</b> {count} товаров\n\n"
        "❓ Добавить все товары на склад?"
    )
    
    MASS_ADD_SUCCESS = (
        "✅ <b>Товары успешно добавлены!</b>\n\n"
        "📦 Добавлено товаров: {count}\n"
        "🏷 Базовое название: {name}\n"
        "📂 Категория: {category}\n"
        "💰 Общая стоимость: {total_value}₽"
    )
    
    # Быстрое добавление товара  
    QUICK_ADD_START = (
        "⚡ <b>Быстрое добавление товара</b>\n\n"
        "Шаг 1/2: Выберите категорию:"
    )
    
    QUICK_ADD_DATA = (
        "⚡ <b>Быстрое добавление товара</b>\n\n"
        "Шаг 2/2: Введите данные товара одним сообщением:\n\n"
        "<b>Формат:</b>\n"
        "<code>Название товара\n"
        "Тип: аккаунт/ключ/промокод\n"
        "Длительность: 1 месяц\n"
        "Цена: 299\n"
        "Контент: логин:пароль</code>\n\n"
        "<b>Пример:</b>\n"
        "<code>Netflix Premium\n"
        "Тип: аккаунт\n"
        "Длительность: 1 месяц\n"
        "Цена: 299\n"
        "Контент: user@mail.com:password123</code>"
    )
    
    QUICK_ADD_SUCCESS = (
        "⚡ <b>Товар быстро добавлен!</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "📂 <b>Категория:</b> {category}\n"
        "📦 <b>Тип:</b> {product_type}\n"
        "⏱ <b>Длительность:</b> {duration}\n"
        "💰 <b>Цена:</b> {price}₽\n\n"
        "Товар готов к продаже!"
    )
    
    # Редактирование товара
    EDIT_PRODUCT_START = (
        "📝 <b>Редактирование товара</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "📂 <b>Категория:</b> {category}\n"
        "📦 <b>Тип:</b> {product_type_display}\n"
        "⏱ <b>Длительность:</b> {duration}\n"
        "💰 <b>Цена:</b> {price}₽\n"
        "📊 <b>Остаток:</b> {stock}\n"
        "📦 <b>Содержимое:</b> {content_preview}\n\n"
        "Выберите, что хотите изменить:"
    )
    
    EDIT_PRODUCT_NAME = (
        "📝 <b>Редактирование названия</b>\n\n"
        "🏷 <b>Текущее название:</b> {current_name}\n\n"
        "Введите новое название товара:"
    )
    
    EDIT_PRODUCT_TYPE = (
        "📝 <b>Редактирование типа товара</b>\n\n"
        "📦 <b>Текущий тип:</b> {current_type}\n\n"
        "Выберите новый тип товара:"
    )
    
    EDIT_PRODUCT_DURATION = (
        "📝 <b>Редактирование длительности</b>\n\n"
        "⏱ <b>Текущая длительность:</b> {current_duration}\n\n"
        "Введите новую длительность:\n\n"
        "Примеры: <code>1 месяц</code>, <code>12 месяцев</code>, <code>lifetime</code>"
    )
    
    EDIT_PRODUCT_PRICE = (
        "📝 <b>Редактирование цены</b>\n\n"
        "💰 <b>Текущая цена:</b> {current_price}₽\n\n"
        "Введите новую цену товара:\n\n"
        "Например: <code>299</code> или <code>99.99</code>"
    )
    
    EDIT_PRODUCT_CONTENT = (
        "📝 <b>Редактирование содержимого</b>\n\n"
        "📦 <b>Тип товара:</b> {product_type_display}\n"
        "📦 <b>Текущее содержимое:</b> <code>{current_content_preview}</code>\n\n"
        "{content_format_message}"
    )
    
    EDIT_PRODUCT_CONFIRMATION = (
        "📝 <b>Подтверждение изменений</b>\n\n"
        "🏷 <b>Товар:</b> {product_name}\n\n"
        "<b>Изменения:</b>\n"
        "{changes_text}\n\n"
        "❓ Сохранить изменения?"
    )
    
    EDIT_PRODUCT_SUCCESS = (
        "✅ <b>Товар успешно обновлен!</b>\n\n"
        "🏷 <b>Название:</b> {name}\n"
        "📂 <b>Категория:</b> {category}\n"
        "📦 <b>Тип:</b> {product_type_display}\n"
        "⏱ <b>Длительность:</b> {duration}\n"
        "💰 <b>Цена:</b> {price}₽\n"
        "📊 <b>Остаток:</b> {stock}\n\n"
        "Товар обновлен в каталоге."
    )
    
    # Предупреждения
    NO_CATEGORIES_WARNING = (
        "⚠️ <b>Категории не найдены</b>\n\n"
        "Для работы со складом необходимо создать хотя бы одну категорию.\n\n"
        "Сначала создайте категорию, а затем добавляйте в неё товары."
    )
    
    # Ошибки
    ERROR_PRODUCT_NOT_FOUND = "❌ Товар не найден или удален"
    ERROR_NO_STOCK = "❌ Товар закончился на складе"
    ERROR_USER_NOT_FOUND = "❌ Пользователь не найден или не запускал бота.\n\nПроверьте:\n• Правильность написания username (без @)\n• Telegram ID пользователя\n• Что пользователь хотя бы раз запускал бота"
    ERROR_INVALID_PRICE = "❌ Неверный формат цены. Введите число (например: 299 или 99.99)"
    ERROR_INVALID_CONTENT_FORMAT = "❌ Неверный формат данных. Следуйте указанному примеру"
    ERROR_CATEGORY_NOT_FOUND = "❌ Категория не найдена"
    ERROR_ACCESS_DENIED = "❌ У вас нет прав доступа к этой функции"
    ERROR_CATEGORY_NAME_TOO_SHORT = "❌ Название категории должно содержать минимум 2 символа"
    ERROR_CATEGORY_EXISTS = "❌ Категория с таким названием уже существует"
    
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