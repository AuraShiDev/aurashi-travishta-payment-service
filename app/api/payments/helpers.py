from __future__ import annotations

from decimal import Decimal
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.bookings.models import BookingPaymentSchedule


def generate_transaction_id() -> str:
    return f"txn_{uuid.uuid4().hex[:21]}"


def amount_to_paise(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def money(value: Decimal | str | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


async def get_installment(
    db: AsyncSession, booking_id: str, installment_no: int
) -> BookingPaymentSchedule:
    stmt = select(BookingPaymentSchedule).where(
        BookingPaymentSchedule.booking_id == booking_id,
        BookingPaymentSchedule.installment_no == installment_no,
    )
    result = await db.execute(stmt)
    installment = result.scalar_one_or_none()

    if not installment:
        raise HTTPException(status_code=404, detail="Invalid installment number")
    if installment.status == "PAID":
        raise HTTPException(status_code=409, detail="Installment already paid")
    return installment
