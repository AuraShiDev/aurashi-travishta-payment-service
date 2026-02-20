from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.api.payments.models import Invoice, PaymentTransaction
from app.core.config import Config
from app.invoices.lambda_pdf import (
    build_invoice_lambda_payload,
    generate_pdf_via_lambda,
)


async def generate_invoice_number(session: AsyncSession) -> str:
    year = datetime.utcnow().year
    result = await session.execute(select(func.count(Invoice.id)))
    count = result.scalar() or 0
    return f"INV-{year}-{str(count + 1).zfill(6)}"


async def generate_invoice_for_payment(
    txn: PaymentTransaction,
    session: AsyncSession,
    customer_name: str | None = None,
    package_name: str | None = None,
) -> Invoice | None:
    existing = (
        await session.execute(
            select(Invoice).where(Invoice.transaction_id == txn.id)
        )
    ).scalars().first()
    if existing:
        return existing
    if not Config.INVOICE_PDF_ENABLED:
        return None

    invoice_number = await generate_invoice_number(session)
    invoice = Invoice(
        invoice_no=invoice_number,
        booking_id=txn.booking_id,
        booking_public_id=txn.booking_public_id,
        transaction_id=txn.id,
        transaction_public_id=txn.transaction_id,
        amount=txn.amount,
        currency=txn.currency,
        status="ISSUED",
        tax_amount=Decimal("0.00"),
    )
    session.add(invoice)
    await session.flush()

    payload = build_invoice_lambda_payload(
        invoice_number=invoice_number,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        booking_id=txn.booking_public_id,
        customer_name=customer_name or "Customer",
        package_name=package_name or "Travel Package",
        total_amount=str(txn.amount),
        file_name=invoice_number,
    )
    print("Generated Lambda Payload:", payload)
    invoice.pdf_url = await generate_pdf_via_lambda(payload)
    session.add(invoice)
    return invoice
