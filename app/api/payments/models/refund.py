from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, DateTime, Numeric, String
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class Refund(SQLModel, table=True):
    __tablename__ = "refunds"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    refund_id: str = Field(
        sa_column=Column("refund_id", String(25), unique=True, nullable=False)
    )

    transaction_id: uuid.UUID = Field(nullable=False)
    amount: Decimal | None = Field(sa_column=Column(Numeric(12, 2)))
    gateway_refund_id: str | None = Field(default=None, sa_column=Column(String(100)))

    status: str | None = Field(default=None, sa_column=Column(String(20)))
    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
