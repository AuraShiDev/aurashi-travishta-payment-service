from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bookings.schemas import (
    CreateInstallmentsRequest,
    CreateInstallmentsResponse,
    InstallmentScheduleItem,
)
from app.api.bookings.service import create_installments
from app.db.main import get_session

bookings_router = APIRouter()


@bookings_router.post(
    "/payment-schedule",
    response_model=CreateInstallmentsResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking_payment_schedule(
    payload: CreateInstallmentsRequest,
    session: AsyncSession = Depends(get_session),
):
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

    return CreateInstallmentsResponse(
        schedules=[
            InstallmentScheduleItem(
                bookingId=item.booking_id,
                bookingPublicId=item.booking_public_id,
                installmentNo=item.installment_no,
                dueAmount=item.due_amount,
                dueDate=item.due_date,
                status=item.status,
            )
            for item in schedules
        ]
    )
