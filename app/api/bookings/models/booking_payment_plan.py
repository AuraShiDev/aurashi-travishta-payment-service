from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, DateTime, Numeric
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class BookingPaymentPlan(SQLModel, table=True):
    __tablename__ = "booking_payment_plan"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    booking_id: uuid.UUID = Field(nullable=False)

    total_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    number_of_installments: int = Field(nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
