from __future__ import annotations

import json
from decimal import Decimal
import uuid

import hmac
import hashlib

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
import razorpay
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bookings.models import BookingPaymentSchedule
from app.api.payments.models import PaymentTransaction
from app.api.payments.schemas import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
)
from app.api.payments.models import PaymentWebhook
from app.core.config import Config
from app.core.exceptions import ExternalServiceError
from app.core.middlewares import logger
from app.core.request_context import get_idempotency_key, get_razorpay_signature_key, is_valid_user, _get_user_context
from app.db.main import get_session
from app.utils.booking_service import extract_booking_public_id, fetch_booking_details, update_booking_status_service

payments_router = APIRouter()


def _generate_transaction_id() -> str:
    return f"txn_{uuid.uuid4().hex[:21]}"


def _amount_to_paise(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())

async def get_installment(db, booking_id: str, installment_no: int):
    stmt = select(BookingPaymentSchedule).where(
        BookingPaymentSchedule.booking_id == booking_id,
        BookingPaymentSchedule.installment_no == installment_no
    )

    result = await db.execute(stmt)
    installment = result.scalar_one_or_none()

    if not installment:
        raise HTTPException(
            status_code=404,
            detail="Invalid installment number"
        )

    if installment.status == "PAID":
        raise HTTPException(
            status_code=409,
            detail="Installment already paid"
        )

    return installment

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
    is_valid_user(request)
    user_context = _get_user_context(request)
    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay keys are not configured",
        )
    idempotency_key = get_idempotency_key(request)
    stmt = select(PaymentTransaction).where(
        PaymentTransaction.idempotency_key == idempotency_key
    )
    existing_payment = (await session.execute(stmt)).scalars().first()
    if existing_payment:
        if not existing_payment.gateway_order_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotent request exists without gateway order",
            )
        return PaymentInitiateResponse(
            razorpayOrderId=existing_payment.gateway_order_id,
            keyId=Config.RAZORPAY_KEY_ID,
            amount=existing_payment.amount,
            currency=existing_payment.currency,
        )

    booking = await fetch_booking_details(
        str(payload.booking_id),
        user_context.user_id
    )
    booking_public_id = extract_booking_public_id(booking)
    if not booking_public_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bookingPublicId missing from booking service response",
        )

    booking_amount = booking.get("amount")
    booking_currency = booking.get("currency")
    if booking_amount is not None and Decimal(str(booking_amount)) != payload.amount:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Amount mismatch with booking",
        )
    if booking_currency is not None and str(booking_currency).upper() != payload.currency.upper():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Currency mismatch with booking",
        )

    if booking.get("payment_status") == "PAID":
        raise HTTPException(400, "Already paid")
    amount = payload.amount
    total_payable_amount = Decimal(str(booking.get("total_payable_amount", "0")))
    # 3️⃣ Determine amount
    if payload.payment_type == "FULL":
        total_payable_amount = Decimal(str(booking.get("total_payable_amount", "0")))
        total_paid_amount = Decimal(str(booking.get("total_paid_amount", "0")))
        amount = total_payable_amount - total_paid_amount
        amount = amount.quantize(Decimal("0.01"))
        if amount <= 0:
            raise HTTPException(400, "No pending amount")
        installment_no = None
    elif payload.payment_type == "PART":

        if payload.installment_no is None:
            raise HTTPException(400, "Installment number required")

        installment = await get_installment(
            session,
            booking.get("id"),
            payload.installment_no
        )

        amount = installment.due_amount
        installment_no = payload.installment_no
    else:
        raise HTTPException(400, "Invalid payment mode")

    client = razorpay.Client(
        auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET)
    )

    try:
        order = client.order.create(
            {
                "amount": _amount_to_paise(amount),
                "currency": payload.currency,
                "receipt": str(payload.booking_id),
                "payment_capture": 1,
            }
        )
    except Exception as exc:  # pragma: no cover - depends on external API
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Razorpay order",
        ) from exc

    payment = PaymentTransaction(
        transaction_id=_generate_transaction_id(),
        booking_id=payload.booking_id,
        booking_public_id=booking_public_id,
        user_id=user_context.user_id,
        amount=amount,
        currency=payload.currency,
        payment_type=payload.payment_type,
        installment_no=installment_no,
        installment_total=2,
        gateway="RAZORPAY",
        gateway_order_id=order.get("id"),
        status="INITIATED",
        idempotency_key=idempotency_key,
    )

    session.add(payment)
    await session.commit()

    return PaymentInitiateResponse(
        razorpayOrderId=payment.gateway_order_id,
        keyId=Config.RAZORPAY_KEY_ID,
        amount=payment.amount,
        currency=payment.currency,
    )


@payments_router.post(
    "/verify",
    response_model=PaymentVerifyResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_payment(
    payload: PaymentVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    if not Config.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay key secret is not configured",
        )

    message = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode()
    generated = hmac.new(
        key=Config.RAZORPAY_KEY_SECRET.encode(),
        msg=message,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(generated, payload.razorpay_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )

    result = await session.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.gateway_order_id == payload.razorpay_order_id
        )
    )
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment transaction not found",
        )

    payment.gateway_payment_id = payload.razorpay_payment_id
    payment.status = "PENDING"
    session.add(payment)
    await session.commit()

    return PaymentVerifyResponse(status="VERIFIED")


@payments_router.post("/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    x_razorpay_signature = get_razorpay_signature_key(request)
    if not Config.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay webhook secret is not configured",
        )
    print(f"Razorpay webhook received: {request}")
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    print(f"Razorpay webhook sig: {x_razorpay_signature}")
    print(f"Razorpay webhook secret: {Config.RAZORPAY_WEBHOOK_SECRET}")
    print(f"Razorpay webhook body: {body_str}")
    razorpay_client = razorpay.Client(
        auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET)
    )
    try:
        razorpay_client.utility.verify_webhook_signature(
            body_str,
            x_razorpay_signature,
            Config.RAZORPAY_WEBHOOK_SECRET
        )
    except Exception as exc:
        print(f"Razorpay webhook ex: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc
    raw_payload = json.loads(body_str)
    print(f"Razorpay webhook received: {raw_payload}")
    payment_payload = (
        raw_payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )
    event_id = payment_payload.get("id")  # Razorpay uses 'id'
    event_type = raw_payload.get("event")

    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook event_id missing",
        )

    existing = await session.execute(
        select(PaymentWebhook).where(PaymentWebhook.event_id == event_id)
    )
    if existing.scalars().first():
        return {"status": "ok"}

    webhook = PaymentWebhook(
        gateway="RAZORPAY",
        event_id=event_id,
        event_type=event_type,
        payload=raw_payload,
        processed=False,
    )
    session.add(webhook)

    order_id = payment_payload.get("order_id")
    payment_id = payment_payload.get("id")
    amount = Decimal(payment_payload.get("amount")) / Decimal(100)

    if order_id:
        # result = await session.execute(
        #     select(PaymentTransaction).where(
        #         PaymentTransaction.gateway_order_id == order_id
        #     ).with_for_update()
        # )
        # payment = result.scalars().first()
        # if payment_id:
        #     payment.gateway_payment_id = payment_id
        if event_type == "payment.captured":
            await handle_payment_success(order_id, payment_id, amount, session)
            # payment.status = "SUCCESS"
        elif event_type == "payment.failed":
            await handle_payment_failed(payment_payload, session)
            # payment.status = "FAILED"
            # session.add(payment)

    webhook.processed = True
    session.add(webhook)
    await session.commit()

    return {"status": "ok"}


async def handle_payment_success(order_id : str,
                                 payment_id : str,
                                 amount: Decimal,
                                 session: AsyncSession):

    # 🔐 Row-level lock to prevent race condition
    stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.gateway_order_id == order_id)
        .with_for_update()
    )

    result = await session.execute(stmt)
    txn = result.scalar_one_or_none()

    if not txn:
        return

    # Idempotency: already processed
    if txn.status == "SUCCESS":
        return

    txn.status = "SUCCESS"
    txn.gateway_payment_id = payment_id

    # 🔹 Update installment schedule
    if txn.installment_no:
        sched_stmt = (
            select(BookingPaymentSchedule)
            .where(
                BookingPaymentSchedule.booking_id == txn.booking_id,
                BookingPaymentSchedule.installment_no == txn.installment_no
            )
            .with_for_update()
        )

        sched_result = await session.execute(sched_stmt)
        schedule = sched_result.scalar_one_or_none()

        if schedule and schedule.status != "PAID":
            schedule.status = "PAID"
            session.add(schedule)

    session.add(txn)
    await session.commit()

    try :
        # 🔹 Now update Booking Service
        await update_booking_status_service(
            booking_id=txn.booking_id,
            amount_paid=amount,
            booking_status="SUCCESS",
            user_id=txn.user_id,
        )
    except httpx.HTTPError as exc:
        await session.rollback()
        raise ExternalServiceError(f"Payment schedule creation failed: {str(exc)}")


async def handle_payment_failed(payload: dict, session: AsyncSession):

    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    error_code = payment_entity.get("error_code")
    error_description = payment_entity.get("error_description")

    if not order_id:
        return

    # 🔐 Row-level lock to avoid race conditions
    stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.gateway_order_id == order_id)
        .with_for_update()
    )

    result = await session.execute(stmt)
    txn = result.scalar_one_or_none()

    if not txn:
        return

    # 🛑 Idempotency: If already SUCCESS, do nothing
    if txn.status == "SUCCESS":
        return

    # 🛑 If already FAILED, do nothing
    if txn.status == "FAILED":
        return

    # 🔹 Update transaction
    txn.status = "FAILED"
    txn.gateway_payment_id = payment_id
    txn.failure_code = error_code
    txn.failure_reason = error_description

    session.add(txn)

    # 🔹 Installment stays PENDING (important)
    # Optional: you can track failure count if needed

    await session.commit()