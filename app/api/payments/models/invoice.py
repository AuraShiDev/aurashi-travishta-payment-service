from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, DateTime, Numeric, String
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    invoice_no: str = Field(
        sa_column=Column("invoice_no", String(30), unique=True, nullable=False)
    )

    booking_id: uuid.UUID = Field(nullable=False)
    booking_public_id: str = Field(
        sa_column=Column("booking_public_id", String(20), nullable=False)
    )

    transaction_id: uuid.UUID = Field(nullable=False)
    transaction_public_id: str = Field(
        sa_column=Column("transaction_public_id", String(25), nullable=False)
    )

    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    currency: str | None = Field(
        default="INR", sa_column=Column(String(10), server_default="INR")
    )

    status: str | None = Field(
        default="ISSUED", sa_column=Column(String(20), server_default="ISSUED")
    )
    issued_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
