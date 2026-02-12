from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class CreateInstallmentsRequest(BaseModel):
    booking_id: Annotated[UUID, Field(alias="bookingId")]
    booking_public_id: Annotated[str, Field(alias="bookingPublicId")]
    total_amount: Annotated[Decimal, Field(alias="totalAmount")]
    number_of_installments: Annotated[int, Field(alias="numberOfInstallments")] = 2

    model_config = {"populate_by_name": True}


class InstallmentScheduleItem(BaseModel):
    booking_id: Annotated[UUID, Field(alias="bookingId")]
    booking_public_id: Annotated[str, Field(alias="bookingPublicId")]
    installment_no: Annotated[int, Field(alias="installmentNo")]
    due_amount: Annotated[Decimal, Field(alias="dueAmount")]
    due_date: Annotated[date | None, Field(alias="dueDate")]
    status: str

    model_config = {"populate_by_name": True}


class CreateInstallmentsResponse(BaseModel):
    schedules: list[InstallmentScheduleItem]

    model_config = {"populate_by_name": True}
