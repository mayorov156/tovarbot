from sqlalchemy import BigInteger, String, Text, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from .database import Base


class OrderStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    
    # Баланс пользователя
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Реферальная система
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    referral_earnings: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Промокод пользователя
    promo_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=True)
    
    # Статистика
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    referrer: Mapped["User"] = relationship("User", remote_side=[id], back_populates="referrals")
    referrals: Mapped[list["User"]] = relationship("User", back_populates="referrer")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    referral_records: Mapped[list["Referral"]] = relationship("Referral", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Категория
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    
    # Остатки
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    digital_content: Mapped[str] = mapped_column(Text, nullable=True)  # Цифровой товар (ключи, коды и т.д.)
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_unlimited: Mapped[bool] = mapped_column(Boolean, default=False)  # Неограниченный товар
    
    # Статистика
    total_sold: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Пользователь
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Товар
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    # Цены
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Статус
    status: Mapped[str] = mapped_column(String(50), default=OrderStatus.PENDING.value)
    
    # Выдача товара
    delivered_content: Mapped[str] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Комментарии
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="orders")
    product: Mapped["Product"] = relationship("Product", back_populates="orders")


class Referral(Base):
    __tablename__ = "referrals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Пользователь, который получил награду
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # Заказ, за который получена награда
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Сумма награды
    reward_amount: Mapped[float] = mapped_column(Float, nullable=False)
    reward_percent: Mapped[float] = mapped_column(Float, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="referral_records")
    order: Mapped["Order"] = relationship("Order")