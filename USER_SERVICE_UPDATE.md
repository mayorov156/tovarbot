# Обновление UserService - Просмотр информации о пользователе

## Новые методы в UserService

### 1. `get_user_brief_info(user_id: int) -> Optional[dict]`
Получает краткую информацию о пользователе для выдачи товара.

**Возвращает:**
```python
{
    "user": User,
    "total_orders": int,
    "total_spent": float,
    "recent_orders": List[Order],
    "has_orders": bool,
    "is_active_buyer": bool,
    "is_regular_buyer": bool,
    "is_vip_buyer": bool
}
```

### 2. `search_user_by_username(username: str) -> Optional[User]`
Находит пользователя по username (с @ или без).

### 3. `search_user_by_id(user_id: int) -> Optional[User]`
Находит пользователя по Telegram ID.

### 4. `search_user_by_referral_code(referral_code: str) -> Optional[User]`
Находит пользователя по реферальному коду.

### 5. `search_user_by_promo_code(promo_code: str) -> Optional[User]`
Находит пользователя по промокоду.

### 6. `search_user_flexible(query: str) -> Optional[User]`
Гибкий поиск пользователя по различным параметрам:
- ID (число)
- Username (с @ или без)
- Реферальный код
- Промокод

### 7. `get_user_orders_summary(user_id: int) -> dict`
Получает сводку заказов пользователя.

**Возвращает:**
```python
{
    "user_found": bool,
    "user": User,
    "total_orders": int,
    "pending_orders": int,
    "paid_orders": int,
    "delivered_orders": int,
    "cancelled_orders": int,
    "total_spent": float,
    "orders_by_status": dict,
    "recent_orders": List[Order]
}
```

### 8. `get_user_activity_level(user_id: int) -> str`
Определяет уровень активности пользователя:
- `"new"` - Новый пользователь (0 заказов)
- `"occasional"` - Случайный покупатель (1-2 заказа)
- `"regular"` - Регулярный покупатель (3-5 заказов)
- `"active"` - Активный покупатель (6-10 заказов)
- `"vip"` - VIP клиент (>10 заказов или >1000₽)

### 9. `get_user_trust_score(user_id: int) -> dict`
Получает оценку доверия к пользователю.

**Возвращает:**
```python
{
    "score": int,  # 0-100
    "level": str,  # "high", "medium", "low", "new"
    "factors": List[str],
    "total_orders": int,
    "successful_orders": int,
    "cancelled_orders": int,
    "account_age_days": int
}
```

## Новые методы в UserRepository

### 1. `get_by_promo_code(promo_code: str) -> Optional[User]`
Находит пользователя по промокоду.

### 2. `get_user_orders(user_id: int) -> List[Order]`
Получает все заказы пользователя с информацией о товарах.

### 3. `search_users_flexible(query: str, limit: int = 10) -> List[User]`
Гибкий поиск пользователей по различным параметрам.

### 4. `get_user_statistics(user_id: int) -> dict`
Получает статистику пользователя.

### 5. `get_recent_user_orders(user_id: int, limit: int = 5) -> List[Order]`
Получает последние заказы пользователя.

### 6. `get_users_by_activity_level(level: str, limit: int = 10) -> List[User]`
Получает пользователей по уровню активности.

## Новые функции форматирования в utils/formatters.py

### 1. `format_user_brief_info(user_info: dict) -> str`
Форматирует краткую информацию о пользователе для выдачи товара.

### 2. `format_user_search_result(user: dict) -> str`
Форматирует результат поиска пользователя.

### 3. `format_user_orders_summary(summary: dict) -> str`
Форматирует сводку заказов пользователя.

### 4. `format_user_trust_score(trust_info: dict) -> str`
Форматирует оценку доверия к пользователю.

### 5. `format_user_activity_level(activity_level: str) -> str`
Форматирует уровень активности пользователя.

### 6. `format_user_for_delivery(user_info: dict) -> str`
Форматирует информацию о пользователе для выдачи товара.

## Примеры использования

### Поиск пользователя
```python
user_service = UserService(session)

# Поиск по username
user = await user_service.search_user_by_username("@username")

# Гибкий поиск
user = await user_service.search_user_flexible("123456789")  # По ID
user = await user_service.search_user_flexible("@username")  # По username
user = await user_service.search_user_flexible("ABC12345")   # По реферальному коду
user = await user_service.search_user_flexible("PROMO123")   # По промокоду
```

### Получение информации о пользователе
```python
# Краткая информация для выдачи
brief_info = await user_service.get_user_brief_info(user_id)
if brief_info:
    text = format_user_brief_info(brief_info)
    print(text)

# Сводка заказов
summary = await user_service.get_user_orders_summary(user_id)
if summary["user_found"]:
    text = format_user_orders_summary(summary)
    print(text)

# Оценка доверия
trust_info = await user_service.get_user_trust_score(user_id)
text = format_user_trust_score(trust_info)
print(text)
```

### Определение уровня активности
```python
activity_level = await user_service.get_user_activity_level(user_id)
formatted_level = format_user_activity_level(activity_level)
print(formatted_level)
```

## Особенности

1. **Гибкий поиск** - поддерживает поиск по ID, username, реферальному коду и промокоду
2. **Оценка доверия** - учитывает количество заказов, успешные/отмененные заказы, возраст аккаунта
3. **Уровни активности** - автоматическое определение статуса пользователя
4. **Форматирование** - готовые функции для красивого отображения информации
5. **Статистика** - детальная информация о заказах и активности пользователя

Эти методы позволяют администраторам быстро получать всю необходимую информацию о пользователе перед выдачей товара, оценивать его надежность и активность. 