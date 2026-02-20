from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.payments.schemas import (
    InvoiceSignedUrlResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    RefundRequest,
    RefundResponse,
)
from app.api.payments.services.payment_service import (
    generate_invoice_signed_url_service,
    initiate_payment_service,
    initiate_refund_service,
    verify_payment_service,
)
from app.api.payments.services.webhook_service import process_webhook_service
from app.db.main import get_session
payments_router = APIRouter()


@payments_router.post(
    "/initiate",
    response_model=PaymentInitiateResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def initiate_payment(
    request: Request,
    payload: PaymentInitiateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await initiate_payment_service(request, payload, session)


@payments_router.post(
    "/refund",
    response_model=RefundResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def initiate_refund(
    payload: RefundRequest,
    session: AsyncSession = Depends(get_session),
):
    return await initiate_refund_service(payload, session)


@payments_router.post(
    "/verify",
    response_model=PaymentVerifyResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_payment(
    payload: PaymentVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    return await verify_payment_service(payload, session)


@payments_router.post("/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    return await process_webhook_service(request, session)


@payments_router.get(
    "/invoices/{invoice_no}/signed-url",
    response_model=InvoiceSignedUrlResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def generate_invoice_signed_url(
    invoice_no: str,
    expires_in: int = 3600,
    session: AsyncSession = Depends(get_session),
):
    return await generate_invoice_signed_url_service(
        invoice_no=invoice_no,
        session=session,
        expires_in=expires_in,
    )
