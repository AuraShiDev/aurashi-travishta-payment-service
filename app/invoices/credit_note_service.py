from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.payments.models import CreditNote, Invoice, RefundTransaction
from app.core.config import Config
from app.invoices.lambda_pdf import (
    build_credit_note_lambda_payload,
    generate_pdf_via_lambda,
)


def generate_credit_note_number() -> str:
    return f"CN-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"


async def generate_credit_note_for_refund(
    refund_record: RefundTransaction,
    session: AsyncSession,
) -> CreditNote | None:
    existing = (
        await session.execute(
            select(CreditNote).where(
                CreditNote.refund_transaction_id == refund_record.id
            )
        )
    ).scalars().first()
    if existing:
        return existing
    if not Config.INVOICE_PDF_ENABLED:
        return None

    invoice = (
        await session.execute(
            select(Invoice).where(
                Invoice.transaction_id == refund_record.payment_transaction_id
            )
        )
    ).scalars().first()
    if not invoice:
        return None

    credit_note_number = generate_credit_note_number()
    credit_note = CreditNote(
        credit_note_number=credit_note_number,
        invoice_id=invoice.id,
        refund_transaction_id=refund_record.id,
        amount=refund_record.amount,
    )
    session.add(credit_note)
    await session.flush()

    payload = build_credit_note_lambda_payload(
        credit_note_number=credit_note_number,
        invoice_number=invoice.invoice_no,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        booking_id=invoice.booking_public_id,
        customer_name="Customer",
        package_name="Travel Package",
        total_amount=str(invoice.amount),
        refund_amount=str(refund_record.amount),
        file_name=credit_note_number,
    )
    credit_note.pdf_url = await generate_pdf_via_lambda(payload)
    session.add(credit_note)
    return credit_note
