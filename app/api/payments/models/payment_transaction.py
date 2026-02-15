from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class PaymentTransaction(SQLModel, table=True):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        Index("idx_payment_transaction_id", "transaction_id"),
        Index("idx_payment_booking_id", "booking_id"),
        Index("idx_payment_gateway", "gateway"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    transaction_id: str = Field(
        sa_column=Column("transaction_id", String(25), unique=True, nullable=False)
    )

    booking_id: uuid.UUID = Field(nullable=False)
    booking_public_id: str = Field(
        sa_column=Column("booking_public_id", String(20), nullable=False)
    )

    user_id: uuid.UUID = Field(nullable=False)

    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    currency: str = Field(
        default="INR", sa_column=Column(String(10), nullable=False)
    )

    payment_type: str = Field(sa_column=Column(String(20), nullable=False))
    installment_no: int | None = Field(default=None, sa_column=Column(Integer))
    installment_total: int | None = Field(default=None, sa_column=Column(Integer))

    gateway: str | None = Field(default=None, sa_column=Column(String(30)))
    gateway_order_id: str | None = Field(default=None, sa_column=Column(String(100)))
    gateway_payment_id: str | None = Field(default=None, sa_column=Column(String(100)))

    status: str = Field(sa_column=Column(String(20), nullable=False))
    refund_amount: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(12, 2))
    )
    refund_status: str = Field(
        default="NONE", sa_column=Column(String(20), nullable=False, server_default="NONE")
    )
    idempotency_key: str = Field(
        sa_column=Column("idempotency_key", String(100), unique=True, nullable=False)
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )
