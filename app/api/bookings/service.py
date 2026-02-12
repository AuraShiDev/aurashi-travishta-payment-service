from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.bookings.models import BookingPaymentPlan, BookingPaymentSchedule


async def create_installments(
    db: AsyncSession,
    booking_id: uuid.UUID,
    booking_public_id: str,
    total_amount: Decimal,
    number_of_installments: int = 2,
) -> list[BookingPaymentSchedule]:
    plan_stmt = select(BookingPaymentPlan).where(
        BookingPaymentPlan.booking_id == booking_id
    )
    plan_result = await db.execute(plan_stmt)
    existing_plan = plan_result.scalars().first()

    stmt = select(BookingPaymentSchedule).where(
        BookingPaymentSchedule.booking_id == booking_id
    )
    result = await db.execute(stmt)
    existing = result.scalars().all()
    if existing:
        if not existing_plan:
            plan = BookingPaymentPlan(
                id=uuid.uuid4(),
                booking_id=booking_id,
                total_amount=Decimal(total_amount).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                number_of_installments=number_of_installments,
            )
            db.add(plan)
            await db.commit()
        return existing

    if number_of_installments < 2:
        raise ValueError("Installments must be >= 2")
    if number_of_installments != 2:
        raise ValueError("Only 2-installment schedule is supported")
    if total_amount <= 0:
        raise ValueError("Invalid total amount")

    total_amount = Decimal(total_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    first_amount = (total_amount * Decimal("0.25")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    remaining_amount = (total_amount - first_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if not existing_plan:
        plan = BookingPaymentPlan(
            id=uuid.uuid4(),
            booking_id=booking_id,
            total_amount=total_amount,
            number_of_installments=number_of_installments,
        )
        db.add(plan)

    installments = [
        BookingPaymentSchedule(
            id=uuid.uuid4(),
            booking_id=booking_id,
            booking_public_id=booking_public_id,
            installment_no=1,
            due_amount=first_amount,
            due_date=date.today(),
            status="PENDING",
        ),
        BookingPaymentSchedule(
            id=uuid.uuid4(),
            booking_id=booking_id,
            booking_public_id=booking_public_id,
            installment_no=2,
            due_amount=remaining_amount,
            due_date=date.today() + timedelta(days=7),
            status="PENDING",
        ),
    ]

    db.add_all(installments)
    await db.commit()
    return installments
