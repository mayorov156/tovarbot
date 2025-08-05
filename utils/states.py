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