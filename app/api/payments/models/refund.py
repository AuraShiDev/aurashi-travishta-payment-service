from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class RefundTransaction(SQLModel, table=True):
    __tablename__ = "refund_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    payment_transaction_id: uuid.UUID = Field(
        sa_column=Column(
            "payment_transaction_id",
            ForeignKey("payment_transactions.id"),
            nullable=False,
        )
    )
    refund_id: str = Field(
        sa_column=Column("refund_id", String(100), unique=True, nullable=False)
    )
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    status: str = Field(sa_column=Column(String(20), nullable=False))
    reason: str | None = Field(default=None, sa_column=Column(Text))
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
