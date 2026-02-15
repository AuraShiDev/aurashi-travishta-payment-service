from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bookings.helpers import to_schedule_response
from app.api.bookings.schemas import CreateInstallmentsRequest, CreateInstallmentsResponse
from app.api.bookings.service import create_installments


async def create_booking_payment_schedule_service(
    payload: CreateInstallmentsRequest,
    session: AsyncSession,
) -> CreateInstallmentsResponse:
    try:
        schedules = await create_installments(
            db=session,
            booking_id=payload.booking_id,
            booking_public_id=payload.booking_public_id,
            total_amount=payload.total_amount,
            number_of_installments=payload.number_of_installments,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return to_schedule_response(schedules)
