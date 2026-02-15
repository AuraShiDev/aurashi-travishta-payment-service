from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class CreditNote(SQLModel, table=True):
    __tablename__ = "credit_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    credit_note_number: str = Field(
        sa_column=Column("credit_note_number", String(30), unique=True, nullable=False)
    )
    invoice_id: uuid.UUID = Field(
        sa_column=Column("invoice_id", ForeignKey("invoices.id"), nullable=False)
    )
    refund_transaction_id: uuid.UUID = Field(
        sa_column=Column(
            "refund_transaction_id",
            ForeignKey("refund_transactions.id"),
            unique=True,
            nullable=False,
        )
    )
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    pdf_url: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
