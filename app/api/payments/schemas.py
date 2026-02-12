from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PaymentInitiateRequest(BaseModel):
    booking_id: Annotated[UUID, Field(alias="bookingId")]
    amount: Decimal
    currency: str = "INR"
    booking_public_id: Annotated[str, Field(alias="bookingPublicId")]
    user_id: Annotated[UUID, Field(alias="userId")]
    payment_type: Annotated[Literal["FULL", "PART"], Field(alias="paymentType")] = "FULL"
    installment_no: Annotated[int | None, Field(alias="installmentNo")] = None
    installment_total: Annotated[int | None, Field(alias="installmentTotal")] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_installments(self) -> "PaymentInitiateRequest":
        if self.payment_type == "PART":
            if self.installment_no is None or self.installment_total is None:
                raise ValueError(
                    "installmentNo and installmentTotal are required for PART payments"
                )
            if self.installment_no < 1 or self.installment_total < 1:
                raise ValueError("installmentNo and installmentTotal must be positive")
            if self.installment_no > self.installment_total:
                raise ValueError("installmentNo cannot be greater than installmentTotal")
        return self


class PaymentInitiateResponse(BaseModel):
    razorpay_order_id: Annotated[str, Field(alias="razorpayOrderId")]
    key_id: Annotated[str, Field(alias="keyId")]
    amount: Decimal
    currency: str

    model_config = {"populate_by_name": True}


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: Annotated[str, Field(alias="razorpay_order_id")]
    razorpay_payment_id: Annotated[str, Field(alias="razorpay_payment_id")]
    razorpay_signature: Annotated[str, Field(alias="razorpay_signature")]


class PaymentVerifyResponse(BaseModel):
    status: str
