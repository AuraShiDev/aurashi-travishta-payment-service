from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class IdempotencyRecord(SQLModel, table=True):
    __tablename__ = "idempotency_records"

    key: str = Field(sa_column=Column("key", String(100), primary_key=True))
    request_hash: str | None = Field(default=None, sa_column=Column(Text))
    response: dict | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        sa_column=Column(DateTime, nullable=False, server_default=func.now())
    )
