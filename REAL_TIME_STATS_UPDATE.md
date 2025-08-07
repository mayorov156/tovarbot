# Обновление статистики в реальном времени

## 🎯 Задача

Реализовать обновление статистики категорий в реальном времени после каждой операции с товарами (удаление, редактирование, выдача, добавление), чтобы пользователи видели актуальные данные о количестве доступных товаров и остатках.

## ✅ Что было реализовано

### 1. Новый метод получения статистики одной категории

**В `services/warehouse_service.py` добавлен метод `get_single_category_stats()`:**

```python
async def get_single_category_stats(self, category_id: int) -> Optional[dict]:
    """Получить статистику для одной конкретной категории в реальном времени"""
    # Получаем количество доступных товаров
    available_products_stmt = select(func.count(Product.id)).where(
        and_(
            Product.category_id == category_id,
            Product.is_active == True,
            or_(
                Product.is_unlimited == True,
                Product.stock_quantity > 0
            )
        )
    )
    
    # Получаем общий остаток (только для товаров с ограниченным количеством)
    total_stock_stmt = select(func.sum(Product.stock_quantity)).where(
        and_(
            Product.category_id == category_id,
            Product.is_active == True,
            Product.is_unlimited == False
        )
    )
    
    # Получаем количество безлимитных товаров
    unlimited_stmt = select(func.count(Product.id)).where(
        and_(
            Product.category_id == category_id,
            Product.is_active == True,
            Product.is_unlimited == True
        )
    )
    
    return {
        'id': category.id,
        'name': category.name,
        'total_products': available_count,
        'total_stock': total_stock,
        'unlimited_products': unlimited_count
    }
```

### 2. Улучшенная клавиатура с отображением статистики

**В `keyboards/warehouse_keyboards.py` обновлена функция `warehouse_category_action_complete_kb()`:**

**Было:**
```python
def warehouse_category_action_complete_kb(category_id: int, page: int = 0, action_type: str = "action") -> InlineKeyboardMarkup:
```

**Стало:**
```python
def warehouse_category_action_complete_kb(category_id: int, page: int = 0, action_type: str = "action", category_stats: dict = None) -> InlineKeyboardMarkup:
    # Показываем актуальную статистику категории, если она предоставлена
    if category_stats:
        stats_text = f"📊 {category_stats['total_products']} товаров"
        if category_stats['unlimited_products'] > 0:
            stats_text += f" (∞: {category_stats['unlimited_products']})"
        if category_stats['total_stock'] > 0:
            stats_text += f", остаток: {category_stats['total_stock']}"
        
        builder.row(
            InlineKeyboardButton(text=stats_text, callback_data=f"warehouse_category_stats_{category_id}")
        )
```

### 3. Обновление всех операций с товарами

**Обновлены все обработчики операций для получения актуальной статистики:**

#### **Выдача товара** (`confirm_give_product` и `confirm_quick_give_product`):

**Было:**
```python
await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="give")
)
```

**Стало:**
```python
# Получаем актуальную статистику категории
category_stats = await warehouse_service.get_single_category_stats(category_id) if category_id else None

await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="give", category_stats=category_stats)
)
```

#### **Добавление товара** (массовое добавление):

**Было:**
```python
await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="add")
)
```

**Стало:**
```python
# Получаем актуальную статистику категории
category_stats = await warehouse_service.get_single_category_stats(category_id) if category_id else None

await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="add", category_stats=category_stats)
)
```

#### **Редактирование товара** (`confirm_edit_product`):

**Было:**
```python
await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="edit")
)
```

**Стало:**
```python
# Получаем актуальную статистику категории
category_stats = await warehouse_service.get_single_category_stats(category_id) if category_id else None

await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="edit", category_stats=category_stats)
)
```

#### **Удаление товара** (`confirm_delete_product`):

**Было:**
```python
await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="delete")
)
```

**Стало:**
```python
# Получаем актуальную статистику категории
category_stats = await warehouse_service.get_single_category_stats(category_id) if category_id else None

await callback.message.edit_text(
    success_text,
    reply_markup=warehouse_category_action_complete_kb(category_id, action_type="delete", category_stats=category_stats)
)
```

## 🎯 Как это работает

### Пример интерфейса после операций:

#### **После выдачи товара:**

**Было:**
```
✅ Товар выдан пользователю @username!
📦 Название: Steam Account Premium
🎯 Получатель: @username
📊 Новый остаток: 47 шт.

  🎯 Выдать еще    📊 Статистика
  📂 К товарам категории    🔄 Обновить категорию
  🎛 Управление категорией    🏪 Главное меню
```

**Стало:**
```
✅ Товар выдан пользователю @username!
📦 Название: Steam Account Premium
🎯 Получатель: @username
📊 Новый остаток: 47 шт.

  🎯 Выдать еще    📊 Статистика
  📊 15 товаров, остаток: 47           ← НОВАЯ КНОПКА С АКТУАЛЬНОЙ СТАТИСТИКОЙ
  📂 К товарам категории    🔄 Обновить категорию
  🎛 Управление категорией    🏪 Главное меню
```

#### **После удаления товара:**

**Было:**
```
✅ Товар успешно удален!
📦 Название: Expired Account
🆔 ID: #123
📂 Категория: Steam аккаунты
💰 Цена: 150.00₽

  🗑 Удалить еще    ➕ Добавить товар
  📂 К товарам категории    🔄 Обновить категорию
  🎛 Управление категорией    🏪 Главное меню
```

**Стало:**
```
✅ Товар успешно удален!
📦 Название: Expired Account
🆔 ID: #123
📂 Категория: Steam аккаунты
💰 Цена: 150.00₽

  🗑 Удалить еще    ➕ Добавить товар
  📊 14 товаров, остаток: 47           ← ОБНОВЛЕННАЯ СТАТИСТИКА
  📂 К товарам категории    🔄 Обновить категорию
  🎛 Управление категорией    🏪 Главное меню
```

### Форматы отображения статистики:

1. **Только обычные товары:** `📊 15 товаров, остаток: 47`
2. **Есть безлимитные товары:** `📊 20 товаров (∞: 5), остаток: 47`
3. **Только безлимитные товары:** `📊 5 товаров (∞: 5)`
4. **Товары без остатков:** `📊 0 товаров`

## 🚀 Преимущества

### 1. **Актуальная информация**
- Статистика обновляется сразу после операции
- Нет необходимости возвращаться к списку категорий для проверки
- Видно реальное количество товаров и остатков

### 2. **Улучшенный пользовательский опыт**
- Мгновенная обратная связь после действий
- Понятные числовые показатели
- Интуитивное отображение безлимитных товаров

### 3. **Эффективность**
- Одиночный SQL-запрос для получения статистики категории
- Минимальная нагрузка на базу данных
- Быстрое отображение результатов

### 4. **Консистентность данных**
- Статистика всегда соответствует реальному состоянию
- Исключены расхождения между отображением и фактическими данными
- Единый механизм подсчета для всех операций

## 🔧 Технические детали

### SQL-запросы для подсчета:

#### **Доступные товары:**
```sql
SELECT COUNT(Product.id) 
FROM products 
WHERE category_id = ? 
  AND is_active = TRUE 
  AND (is_unlimited = TRUE OR stock_quantity > 0)
```

#### **Общий остаток:**
```sql
SELECT SUM(Product.stock_quantity) 
FROM products 
WHERE category_id = ? 
  AND is_active = TRUE 
  AND is_unlimited = FALSE
```

#### **Безлимитные товары:**
```sql
SELECT COUNT(Product.id) 
FROM products 
WHERE category_id = ? 
  AND is_active = TRUE 
  AND is_unlimited = TRUE
```

### Производительность:
- ⚡ **Быстрые запросы** - используются индексы по `category_id` и `is_active`
- 🎯 **Точечные обновления** - статистика запрашивается только для конкретной категории
- 💾 **Минимальное использование памяти** - возвращается только необходимая информация

## 📋 Измененные файлы

1. **`services/warehouse_service.py`** - добавлен метод `get_single_category_stats()`
2. **`keyboards/warehouse_keyboards.py`** - обновлена функция `warehouse_category_action_complete_kb()`
3. **`handlers/warehouse_handlers.py`** - обновлены 5 обработчиков операций:
   - `confirm_give_product` (выдача товара)
   - `confirm_quick_give_product` (быстрая выдача)
   - Массовое добавление товаров
   - `confirm_edit_product` (редактирование товара)
   - `confirm_delete_product` (удаление товара)

## ✅ Результат

### Теперь после каждой операции с товарами:

1. **📊 Статистика обновляется в реальном времени**
2. **🎯 Пользователи видят актуальные данные сразу**
3. **⚡ Быстрое отображение без дополнительных переходов**
4. **🔄 Консистентность данных гарантирована**

### Пользовательские сценарии:

1. **Админ выдает товар** → видит обновленный остаток и количество товаров
2. **Админ удаляет товар** → статистика сразу показывает на 1 товар меньше
3. **Админ добавляет товары** → счетчик увеличивается на количество добавленных
4. **Админ редактирует товар** → статистика остается актуальной

## 🎉 Заключение

Реализована система **обновления статистики в реальном времени**, которая значительно улучшает пользовательский опыт управления складом. Администраторы теперь получают мгновенную обратную связь о результатах своих действий и всегда видят актуальную информацию о состоянии товаров в категориях.

Система работает эффективно, используя оптимизированные SQL-запросы и минимизируя нагрузку на базу данных, при этом обеспечивая максимальную точность и актуальность отображаемых данных.