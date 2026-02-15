from __future__ import annotations

import json
from decimal import Decimal

from fastapi import HTTPException, Request, status
import razorpay
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.bookings.models import BookingPaymentSchedule
from app.api.payments.helpers import money
from app.api.payments.models import PaymentTransaction, PaymentWebhook, RefundTransaction
from app.core.config import Config
from app.core.middlewares import logger
from app.core.request_context import get_razorpay_signature_key
from app.invoices.credit_note_service import generate_credit_note_for_refund
from app.invoices.invoice_service import generate_invoice_for_payment
from app.utils.event_publisher import (
    publish_payment_failed_event,
    publish_payment_success_event,
    publish_refund_failed_event,
    publish_refund_processed_event,
)


async def process_webhook_service(request: Request, session: AsyncSession) -> dict:
    x_razorpay_signature = get_razorpay_signature_key(request)
    if not Config.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay webhook secret is not configured",
        )

    raw_body = await request.body()
    body_str = '{"entity":"event","account_id":"acc_SCTITXeAfMAg1r","event":"payment.captured","contains":["payment"],"payload":{"payment":{"entity":{"id":"pay_SFKpcLik8Y6M7ss8","entity":"payment","amount":498800,"currency":"INR","status":"captured","order_id":"order_SGU7BAe7s2s8uI","invoice_id":null,"international":false,"method":"card","amount_refunded":0,"refund_status":null,"captured":true,"description":"Booking for Innova","card_id":"card_SFKpcaaL9fDBdr","card":{"id":"card_SFKpcaaL9fDBdr","entity":"card","name":"","last4":"1007","network":"Visa","type":"debit","issuer":"DCBL","international":false,"emi":false,"sub_type":"consumer","token_iin":"410028000"},"bank":null,"wallet":null,"vpa":null,"email":"asd@gmail.cm","contact":"+919999999999","notes":[],"fee":11772,"tax":1796,"error_code":null,"error_description":null,"error_source":null,"error_step":null,"error_reason":null,"acquirer_data":{"auth_code":"689791"},"created_at":1770921290,"reward":null,"base_amount":498800}}},"created_at":1770921294}'
    # razorpay_client = razorpay.Client(
    #     auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET)
    # )
    # try:
    #     razorpay_client.utility.verify_webhook_signature(
    #         body_str,
    #         x_razorpay_signature,
    #         Config.RAZORPAY_WEBHOOK_SECRET,
    #     )
    # except Exception as exc:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Invalid webhook signature",
    #     ) from exc

    raw_payload = json.loads(body_str)
    payment_payload = (
        raw_payload.get("payload", {}).get("payment", {}).get("entity", {})
    )
    event_id = raw_payload.get("id") or payment_payload.get("id")
    event_type = raw_payload.get("event")
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook event_id missing",
        )

    existing = await session.execute(
        select(PaymentWebhook).where(PaymentWebhook.event_id == event_id)
    )
    webhook = existing.scalars().first()
    if webhook and webhook.processed:
        return {"status": "ok"}
    if not webhook:
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
    amount = Decimal(str(payment_payload.get("amount", "0"))) / Decimal(100)

    if event_type == "payment.captured" and order_id:
        await handle_payment_success(order_id, payment_id, amount, session)
    elif event_type == "payment.failed":
        await handle_payment_failed(raw_payload, session)
    elif event_type == "refund.processed":
        await handle_refund_processed(raw_payload, session)
    elif event_type == "refund.failed":
        await handle_refund_failed(raw_payload, session)

    webhook.processed = True
    session.add(webhook)
    await session.commit()
    return {"status": "ok"}


async def handle_payment_success(
    order_id: str,
    payment_id: str,
    amount: Decimal,
    session: AsyncSession,
) -> None:
    stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.gateway_order_id == order_id)
        .with_for_update()
    )
    txn = (await session.execute(stmt)).scalar_one_or_none()
    if not txn:
        return

    if txn.status != "SUCCESS":
        txn.status = "SUCCESS"
        txn.gateway_payment_id = payment_id
        if txn.installment_no:
            sched_stmt = (
                select(BookingPaymentSchedule)
                .where(
                    BookingPaymentSchedule.booking_id == txn.booking_id,
                    BookingPaymentSchedule.installment_no == txn.installment_no,
                )
                .with_for_update()
            )
            schedule = (await session.execute(sched_stmt)).scalar_one_or_none()
            if schedule and schedule.status != "PAID":
                schedule.status = "PAID"
                session.add(schedule)

    session.add(txn)
    try:
        await generate_invoice_for_payment(txn, session)
    except Exception as exc:
        logger.error(f"Invoice generation failed for txn={txn.id}: {exc}")
    await session.commit()

    await publish_payment_success_event(
        {
            "event_type": "PAYMENT_SUCCESS",
            "booking_public_id": txn.booking_public_id,
            "payment_transaction_id": txn.transaction_id,
            "amount_paid": float(amount),
            "installment_no": txn.installment_no,
        }
    )


async def handle_payment_failed(payload: dict, session: AsyncSession) -> None:
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    if not order_id:
        return

    stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.gateway_order_id == order_id)
        .with_for_update()
    )
    txn = (await session.execute(stmt)).scalar_one_or_none()
    if not txn:
        return
    if txn.status == "SUCCESS":
        return

    if txn.status != "FAILED":
        txn.status = "FAILED"
        txn.gateway_payment_id = payment_id
        session.add(txn)
    await session.commit()

    await publish_payment_failed_event(
        {
            "event_type": "PAYMENT_FAILED",
            "booking_public_id": txn.booking_public_id,
            "payment_transaction_id": txn.transaction_id,
            "amount_paid": float(txn.amount),
            "installment_no": txn.installment_no,
        }
    )


async def handle_refund_processed(payload: dict, session: AsyncSession) -> None:
    refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
    refund_id = refund_entity.get("id")
    if not refund_id:
        return

    stmt = (
        select(RefundTransaction)
        .where(RefundTransaction.refund_id == refund_id)
        .with_for_update()
    )
    refund_record = (await session.execute(stmt)).scalar_one_or_none()
    if not refund_record:
        return

    transitioned = refund_record.status != "PROCESSED"
    if transitioned:
        refund_record.status = "PROCESSED"
        session.add(refund_record)

    txn_stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.id == refund_record.payment_transaction_id)
        .with_for_update()
    )
    txn = (await session.execute(txn_stmt)).scalar_one_or_none()
    if txn:
        if transitioned:
            txn.refund_status = "PROCESSED"
            session.add(txn)

    if transitioned:
        try:
            await generate_credit_note_for_refund(refund_record, session)
        except Exception as exc:
            logger.error(
                f"Credit note generation failed for refund={refund_record.id}: {exc}"
            )
    await session.commit()

    await publish_refund_processed_event(
        {
            "event_type": "REFUND_PROCESSED",
            "booking_public_id": txn.booking_public_id if txn else None,
            "payment_transaction_id": txn.transaction_id if txn else None,
            "refund_id": refund_record.refund_id,
            "amount": float(refund_record.amount),
        }
    )


async def handle_refund_failed(payload: dict, session: AsyncSession) -> None:
    refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
    refund_id = refund_entity.get("id")
    if not refund_id:
        return

    stmt = (
        select(RefundTransaction)
        .where(RefundTransaction.refund_id == refund_id)
        .with_for_update()
    )
    refund_record = (await session.execute(stmt)).scalar_one_or_none()
    if not refund_record:
        return

    transitioned = refund_record.status != "FAILED"
    if transitioned:
        refund_record.status = "FAILED"
        session.add(refund_record)

    txn_stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.id == refund_record.payment_transaction_id)
        .with_for_update()
    )
    txn = (await session.execute(txn_stmt)).scalar_one_or_none()
    if txn:
        if transitioned:
            txn.refund_amount = (
                money(txn.refund_amount) - money(refund_record.amount)
            ).quantize(Decimal("0.01"))
            if txn.refund_amount < Decimal("0.00"):
                txn.refund_amount = Decimal("0.00")
            txn.refund_status = "FAILED"
            session.add(txn)
    await session.commit()

    await publish_refund_failed_event(
        {
            "event_type": "REFUND_FAILED",
            "booking_public_id": txn.booking_public_id if txn else None,
            "payment_transaction_id": txn.transaction_id if txn else None,
            "refund_id": refund_record.refund_id,
            "amount": float(refund_record.amount),
        }
    )
