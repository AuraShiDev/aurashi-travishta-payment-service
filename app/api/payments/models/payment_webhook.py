from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class PaymentWebhook(SQLModel, table=True):
    __tablename__ = "payment_webhooks"
    __table_args__ = (
        Index("idx_payment_webhook_gateway", "gateway"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    gateway: str | None = Field(default=None, sa_column=Column(String(30)))
    event_id: str = Field(
        sa_column=Column("event_id", String(100), unique=True, nullable=False)
    )
    event_type: str | None = Field(default=None, sa_column=Column(String(50)))
    payload: dict | None = Field(default=None, sa_column=Column(JSONB))
    processed: bool = Field(
        default=False, sa_column=Column(Boolean, nullable=False, server_default="false")
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
