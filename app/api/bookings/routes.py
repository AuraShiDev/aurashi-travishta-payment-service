from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bookings.schemas import CreateInstallmentsRequest, CreateInstallmentsResponse
from app.api.bookings.services import create_booking_payment_schedule_service
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
    return await create_booking_payment_schedule_service(payload, session)
