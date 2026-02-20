from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, Request, status
import hmac
import hashlib
import razorpay
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.payments.helpers import amount_to_paise, generate_transaction_id, get_installment, money
from app.api.payments.models import Invoice, PaymentTransaction, RefundTransaction
from app.api.payments.schemas import (
    InvoiceSignedUrlResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    RefundRequest,
    RefundResponse,
)
from app.core.config import Config
from app.core.request_context import _get_user_context, get_idempotency_key, is_valid_user
from app.invoices.storage import generate_presigned_url_from_s3_url
from app.utils.booking_service import extract_booking_public_id, fetch_booking_details


async def initiate_payment_service(
    request: Request,
    payload: PaymentInitiateRequest,
    session: AsyncSession,
) -> PaymentInitiateResponse:
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

    booking = await fetch_booking_details(str(payload.booking_id), user_context.user_id)
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
        raise HTTPException(status_code=400, detail="Already paid")

    amount = payload.amount
    installment_no: int | None = None
    if payload.payment_type == "FULL":
        total_payable_amount = Decimal(str(booking.get("total_payable_amount", "0")))
        total_paid_amount = Decimal(str(booking.get("total_paid_amount", "0")))
        amount = (total_payable_amount - total_paid_amount).quantize(Decimal("0.01"))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="No pending amount")
    elif payload.payment_type == "PART":
        if payload.installment_no is None:
            raise HTTPException(status_code=400, detail="Installment number required")
        installment = await get_installment(session, booking.get("id"), payload.installment_no)
        amount = installment.due_amount
        installment_no = payload.installment_no
    else:
        raise HTTPException(status_code=400, detail="Invalid payment mode")

    client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))
    try:
        order = client.order.create(
            {
                "amount": amount_to_paise(amount),
                "currency": payload.currency,
                "receipt": str(payload.booking_id),
                "payment_capture": 1,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Razorpay order",
        ) from exc

    payment = PaymentTransaction(
        transaction_id=generate_transaction_id(),
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


async def initiate_refund_service(
    payload: RefundRequest, session: AsyncSession
) -> RefundResponse:
    if not Config.RAZORPAY_KEY_ID or not Config.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay keys are not configured",
        )

    refundable_stmt = (
        select(PaymentTransaction)
        .where(
            PaymentTransaction.booking_public_id == payload.booking_public_id,
            PaymentTransaction.status == "SUCCESS",
        )
        .with_for_update()
    )
    transactions = (await session.execute(refundable_stmt)).scalars().all()
    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No successful transactions found for booking",
        )

    remaining_by_txn: list[tuple[PaymentTransaction, Decimal]] = []
    total_refundable = Decimal("0.00")
    for txn in transactions:
        remaining = (money(txn.amount) - money(txn.refund_amount)).quantize(Decimal("0.01"))
        if remaining > 0:
            remaining_by_txn.append((txn, remaining))
            total_refundable += remaining

    request_amount = money(payload.amount)
    if request_amount <= 0 or request_amount > total_refundable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refund amount")

    # client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))
    pending_amount = request_amount
    for txn, remaining in remaining_by_txn:
        if pending_amount <= 0:
            break
        if not txn.gateway_payment_id:
            continue

        refund_for_txn = min(remaining, pending_amount).quantize(Decimal("0.01"))
        if refund_for_txn <= 0:
            continue
        # try:
        #     refund = client.payment.refund(
        #         txn.gateway_payment_id, {"amount": amount_to_paise(refund_for_txn)}
        #     )
        # except Exception as exc:
        #     raise HTTPException(
        #         status_code=status.HTTP_502_BAD_GATEWAY,
        #         detail="Failed to initiate refund with gateway",
        #     ) from exc

        refund_record = RefundTransaction(
            payment_transaction_id=txn.id,
            refund_id='rfnd_124',
            amount=refund_for_txn,
            status="INITIATED",
            reason=payload.reason,
        )
        txn.refund_amount = (money(txn.refund_amount) + refund_for_txn).quantize(Decimal("0.01"))
        txn.refund_status = "INITIATED"
        session.add(refund_record)
        session.add(txn)
        pending_amount = (pending_amount - refund_for_txn).quantize(Decimal("0.01"))

    if pending_amount > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount exceeds gateway-refundable transactions",
        )

    await session.commit()
    return RefundResponse(status="refund initiated", refundedAmount=request_amount)


async def verify_payment_service(
    payload: PaymentVerifyRequest, session: AsyncSession
) -> PaymentVerifyResponse:
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

    stmt = select(PaymentTransaction).where(
        PaymentTransaction.gateway_order_id == payload.razorpay_order_id
    )
    payment = (await session.execute(stmt)).scalars().first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment transaction not found",
        )
    payment.gateway_payment_id = payload.razorpay_payment_id
    # payment.status = "PENDING"
    session.add(payment)
    await session.commit()
    return PaymentVerifyResponse(status="VERIFIED")


async def generate_invoice_signed_url_service(
    invoice_no: str,
    session: AsyncSession,
    expires_in: int = 3600,
) -> InvoiceSignedUrlResponse:
    if expires_in <= 0 or expires_in > 604800:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expiresIn must be between 1 and 604800 seconds",
        )

    invoice = (
        await session.execute(
            select(Invoice).where(Invoice.invoice_no == invoice_no)
        )
    ).scalars().first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )
    if not invoice.pdf_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice PDF URL not available",
        )

    try:
        signed_url = generate_presigned_url_from_s3_url(
            invoice.pdf_url, expires_in=expires_in
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate signed URL",
        ) from exc

    return InvoiceSignedUrlResponse(
        invoiceNo=invoice.invoice_no,
        signedUrl=signed_url,
        expiresIn=expires_in,
    )
