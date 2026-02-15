from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.payments.models import CreditNote, Invoice, RefundTransaction
from app.core.config import Config
from app.invoices.invoice_generator import render_template
from app.invoices.lambda_pdf import generate_pdf_via_lambda


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

    context = {
        "credit_note_number": credit_note_number,
        "invoice_number": invoice.invoice_no,
        "refund_amount": str(refund_record.amount),
        "date": datetime.utcnow().strftime("%d-%m-%Y"),
    }
    html_content = render_template("credit_note.html", context)
    credit_note.pdf_url = await generate_pdf_via_lambda(
        html_content, credit_note_number
    )
    session.add(credit_note)
    return credit_note
