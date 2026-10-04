import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator

# ----------------- User Schemas -----------------
class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    currency_symbol: Optional[str] = "₹"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

# ----------------- Category Schemas -----------------
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field("expense", pattern="^(expense|income)$")
    icon: str = Field("tag", max_length=50)
    color: str = Field("#6366F1", max_length=20)

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, pattern="^(expense|income)$")
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)

# ----------------- Bank Account Schemas -----------------
class BankAccountCreate(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=100)
    account_name: str = Field(..., min_length=1, max_length=100)
    account_number_last4: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    ifsc_code: Optional[str] = Field(None, max_length=20)
    initial_balance: float = Field(0.0, ge=0.0)
    color: Optional[str] = Field("#2563EB", max_length=20)

class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100)
    account_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_number_last4: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    ifsc_code: Optional[str] = Field(None, max_length=20)
    initial_balance: Optional[float] = Field(None, ge=0.0)
    current_balance: Optional[float] = None
    color: Optional[str] = Field(None, max_length=20)

# ----------------- Credit Card Schemas -----------------
class CreditCardCreate(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=100)
    card_name: str = Field(..., min_length=2, max_length=100)
    card_network: str = Field("Visa", max_length=50)
    last_4_digits: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    total_limit: float = Field(..., ge=1.0)
    opening_limit: float = Field(..., ge=0.0)
    billing_day: int = Field(..., ge=1, le=31)
    due_day: int = Field(..., ge=1, le=31)
    card_image_url: Optional[str] = None
    card_color_gradient: Optional[str] = None

class CreditCardUpdate(BaseModel):
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100)
    card_name: Optional[str] = Field(None, min_length=2, max_length=100)
    card_network: Optional[str] = Field(None, max_length=50)
    last_4_digits: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    total_limit: Optional[float] = Field(None, ge=1.0)
    opening_limit: Optional[float] = Field(None, ge=0.0)
    available_limit: Optional[float] = None
    billing_day: Optional[int] = Field(None, ge=1, le=31)
    due_day: Optional[int] = Field(None, ge=1, le=31)
    card_image_url: Optional[str] = None
    card_color_gradient: Optional[str] = None

# ----------------- Trip Schemas -----------------
class TripCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    destination: str = Field(..., min_length=2, max_length=150)
    start_date: datetime.date
    end_date: datetime.date
    budget: float = Field(0.0, ge=0.0)
    description: Optional[str] = None
    status: Optional[str] = Field("active", pattern="^(planned|active|completed)$")
    color: Optional[str] = Field("#06B6D4", max_length=20)

class TripUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    destination: Optional[str] = Field(None, min_length=2, max_length=150)
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    budget: Optional[float] = Field(None, ge=0.0)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(planned|active|completed)$")
    color: Optional[str] = Field(None, max_length=20)

# ----------------- Transaction Schemas -----------------
class TransactionCreate(BaseModel):
    type: str = Field(..., pattern="^(expense|income)$")
    amount: float = Field(..., gt=0.0)
    date: Optional[datetime.date] = None
    category_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    credit_card_id: Optional[int] = None
    trip_id: Optional[int] = None
    tag: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = Field(None, max_length=500)

class TransactionUpdate(BaseModel):
    type: Optional[str] = Field(None, pattern="^(expense|income)$")
    amount: Optional[float] = Field(None, gt=0.0)
    date: Optional[datetime.date] = None
    category_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    credit_card_id: Optional[int] = None
    trip_id: Optional[int] = None
    tag: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = Field(None, max_length=500)

# ----------------- Admin Schemas -----------------
class DateOverrideRequest(BaseModel):
    target_date: datetime.date
