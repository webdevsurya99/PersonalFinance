import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow_naive():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    currency_symbol = Column(String(10), default="₹", nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    # Relationships
    accounts = relationship("BankAccount", back_populates="user", cascade="all, delete-orphan")
    credit_cards = relationship("CreditCard", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="expense") # 'expense' or 'income'
    icon = Column(String(50), nullable=False, default="tag") # Emoji or icon name
    color = Column(String(20), nullable=False, default="#6366F1")
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")

class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_name = Column(String(100), nullable=False)
    account_name = Column(String(100), nullable=False)
    account_number_last4 = Column(String(4), nullable=False)
    ifsc_code = Column(String(20), nullable=True)
    initial_balance = Column(Float, default=0.0, nullable=False)
    current_balance = Column(Float, default=0.0, nullable=False)
    color = Column(String(20), default="#2563EB", nullable=False)
    icon = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="bank_account")

class CreditCard(Base):
    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_name = Column(String(100), nullable=False)
    card_name = Column(String(100), nullable=False)
    card_network = Column(String(50), default="Visa", nullable=False)
    last_4_digits = Column(String(4), nullable=False)
    total_limit = Column(Float, default=0.0, nullable=False)
    opening_limit = Column(Float, default=0.0, nullable=False)
    available_limit = Column(Float, default=0.0, nullable=False)
    billing_day = Column(Integer, nullable=False) # 1 to 31
    due_day = Column(Integer, nullable=False)     # 1 to 31
    card_image_url = Column(String(500), nullable=True)
    card_color_gradient = Column(String(200), default="linear-gradient(135deg, #1e293b 0%, #0f172a 100%)", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="credit_cards")
    transactions = relationship("Transaction", back_populates="credit_card")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    destination = Column(String(150), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Float, default=0.0, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    color = Column(String(20), default="#06B6D4", nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="trips")
    transactions = relationship("Transaction", back_populates="trip")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    credit_card_id = Column(Integer, ForeignKey("credit_cards.id", ondelete="SET NULL"), nullable=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True)
    tag = Column(String(100), nullable=True, index=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    bank_account = relationship("BankAccount", back_populates="transactions")
    credit_card = relationship("CreditCard", back_populates="transactions")
    trip = relationship("Trip", back_populates="transactions")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="due_date", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    link = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="notifications")

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    user = relationship("User", back_populates="audit_logs")
