from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.config import Config
from app.core.middlewares import logger
from app.utils.response import error_response, ErrorDetail


def extract_booking_public_id(booking: dict) -> str | None:
    return (
        booking.get("bookingPublicId")
        or booking.get("booking_public_id")
        or booking.get("publicId")
        or booking.get("public_id")
    )


async def fetch_booking_details(
    booking_id: str,
    user_id: str
) -> dict:
    url = f"{Config.BOOKING_SERVICE_URL}/api/v1/bookings/{booking_id}"
    headers: dict[str, str] = {}
    headers["AuthStatus"] = "AUTHENTICATED"
    headers["UserId"] = user_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        logger.error(f"Unexpected error booking service: {str(exc)}")
        error_response(
            message="An unexpected error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            errors=[ErrorDetail(code="SERVER_ERROR", message=str(exc))]
        )

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    if response.status_code >= status.HTTP_400_BAD_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Booking service returned an error",
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid booking service response",
        ) from exc

    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    if isinstance(data, dict):
        return data
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unexpected booking response format",
    )
