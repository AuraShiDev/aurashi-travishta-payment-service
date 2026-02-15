from __future__ import annotations

from app.api.bookings.models import BookingPaymentSchedule
from app.api.bookings.schemas import CreateInstallmentsResponse, InstallmentScheduleItem


def to_schedule_response(
    schedules: list[BookingPaymentSchedule],
) -> CreateInstallmentsResponse:
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
