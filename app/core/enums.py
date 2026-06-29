from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    CASHIER = "cashier"
    ACCOUNTANT = "accountant"


class SubscriptionPlan(StrEnum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class DerivedSubscriptionStatus(StrEnum):
    MISSING = "missing"


class SaleStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class SalePaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    CLICK = "click"
    PAYME = "payme"
    OTHER = "other"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class DebtTransactionType(StrEnum):
    BORROW = "borrow"
    REPAYMENT = "repayment"
    ADJUSTMENT = "adjustment"


class StockMovementType(StrEnum):
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"
    RETURN = "return"


class OtpPurpose(StrEnum):
    REGISTER = "register"
    PASSWORD_RESET = "password_reset"


class SmsProviderType(StrEnum):
    FAKE = "fake"
    ESKIZ = "eskiz"


def sql_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)
