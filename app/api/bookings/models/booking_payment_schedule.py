from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, Date, DateTime, Index, Numeric, String
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class BookingPaymentSchedule(SQLModel, table=True):
    __tablename__ = "booking_payment_schedule"
    __table_args__ = (
        Index("uq_booking_payment_schedule_booking_installment", "booking_id", "installment_no", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    booking_id: uuid.UUID = Field(nullable=False)
    booking_public_id: str = Field(sa_column=Column(String(20), nullable=False))

    installment_no: int = Field(nullable=False)
    due_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    due_date: date | None = Field(default=None, sa_column=Column(Date))

    status: str = Field(
        default="PENDING", sa_column=Column(String(20), server_default="PENDING")
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
