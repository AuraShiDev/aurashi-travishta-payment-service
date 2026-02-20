from __future__ import annotations

import asyncio
import json

import boto3

from app.core.config import Config


def _lambda_client():
    client_kwargs: dict[str, str] = {}
    if Config.AWS_REGION:
        client_kwargs["region_name"] = Config.AWS_REGION
    if Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_KEY
    return boto3.client("lambda", **client_kwargs)


def build_invoice_lambda_payload(
    *,
    invoice_number: str,
    date: str,
    booking_id: str,
    customer_name: str,
    package_name: str,
    total_amount: str,
    file_name: str = "",
) -> dict:
    return {
        "data": {
            "invoice_number": invoice_number,
            "date": date,
            "booking_id": booking_id,
            "customer_name": customer_name,
            "package_name": package_name,
            "total_amount": total_amount,
        },
        "type": "invoice",
        "fileName": file_name,
    }


def build_credit_note_lambda_payload(
    *,
    credit_note_number: str,
    date: str,
    invoice_number: str,
    booking_id: str,
    customer_name: str,
    package_name: str,
    total_amount: str,
    refund_amount: str,
    file_name: str = "",
) -> dict:
    return {
        "data": {
            "credit_note_number": credit_note_number,
            "invoice_number": invoice_number,
            "date": date,
            "booking_id": booking_id,
            "customer_name": customer_name,
            "package_name": package_name,
            "total_amount": total_amount,
            "refund_amount": refund_amount,
        },
        "type": "credit_note",
        "fileName": file_name,
    }


def _invoke_lambda(payload: dict) -> str:
    if not Config.PDF_LAMBDA_FUNCTION_NAME:
        raise ValueError("PDF_LAMBDA_FUNCTION_NAME is not configured")

    try:
        response = _lambda_client().invoke(
            FunctionName=Config.PDF_LAMBDA_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
    except Exception as exc:
        print(f"[lambda_pdf] invoke failed: {exc}")
        raise

    try:
        lambda_payload = json.loads(response["Payload"].read())
    except Exception as exc:
        print(f"[lambda_pdf] payload parse failed: {exc}")
        raise

    try:
        body = lambda_payload.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            raise ValueError("Invalid Lambda response for PDF generation")
        pdf_url = body.get("url") or body.get("pdf_url")
        if not pdf_url:
            raise ValueError("Invalid Lambda response for PDF generation")
        return str(pdf_url)
    except Exception as exc:
        print(f"[lambda_pdf] response validation failed: {exc}, payload={lambda_payload}")
        raise


async def generate_pdf_via_lambda(payload: dict) -> str:
    return await asyncio.to_thread(_invoke_lambda, payload)
