from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    """Состояния для формы заказа"""
    waiting_for_product = State()
    waiting_for_quantity = State()
    waiting_for_confirmation = State()


class AdminStates(StatesGroup):
    """Состояния для админ панели"""
    waiting_for_product_name = State()
    waiting_for_product_description = State()
    waiting_for_product_price = State()
    waiting_for_product_category = State()
    waiting_for_product_stock = State()
    waiting_for_digital_content = State()
    
    waiting_for_category_name = State()
    waiting_for_category_description = State()
    
    waiting_for_order_content = State()
    waiting_for_cancel_reason = State()
    
    # Состояния для склада
    waiting_for_user_to_give = State()
    waiting_for_product_to_give = State()
    waiting_for_give_quantity = State()
    waiting_for_stock_quantity = State()
    waiting_for_edit_product_field = State()
    waiting_for_new_product_value = State()


class WarehouseAddProductStates(StatesGroup):
    """Состояния для добавления товара на склад"""
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_duration = State()
    waiting_for_content = State()
    waiting_for_price = State()
    waiting_for_confirmation = State()


class WarehouseGiveProductStates(StatesGroup):
    """Состояния для выдачи товара со склада"""
    waiting_for_product = State()
    waiting_for_user = State()
    waiting_for_confirmation = State()


class WarehouseCreateCategoryStates(StatesGroup):
    """Состояния для создания категории"""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_manual_url = State()
    waiting_for_confirmation = State()


class WarehouseMassAddStates(StatesGroup):
    """Состояния для массового добавления товаров"""
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_duration = State()
    waiting_for_price = State()
    waiting_for_content = State()
    waiting_for_confirmation = State()


class WarehouseQuickAddStates(StatesGroup):
    """Состояния для быстрого добавления товара"""
    waiting_for_category = State()
    waiting_for_all_data = State()


class WarehouseEditProductStates(StatesGroup):
    """Состояния для редактирования товара"""
    waiting_for_field_selection = State()
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_duration = State()
    waiting_for_price = State()
    waiting_for_content = State()
    waiting_for_confirmation = State()


class WarehouseQuickGiveStates(StatesGroup):
    """Состояния для быстрой выдачи товара"""
    waiting_for_search = State()
    waiting_for_user = State()
    waiting_for_confirmation = State()


class AdminSettingsStates(StatesGroup):
    """Состояния для редактирования настроек системы"""
    waiting_for_value = State()
    waiting_for_confirmation = State()