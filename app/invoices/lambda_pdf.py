from __future__ import annotations

import asyncio
import json

import boto3

from app.core.config import Config


def _invoke_lambda(html_content: str, file_name: str) -> str:
    if not Config.PDF_LAMBDA_FUNCTION_NAME:
        raise ValueError("PDF_LAMBDA_FUNCTION_NAME is not configured")

    client_kwargs: dict[str, str] = {}
    if Config.AWS_REGION:
        client_kwargs["region_name"] = Config.AWS_REGION
    if Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_KEY

    lambda_client = boto3.client("lambda", **client_kwargs)
    response = lambda_client.invoke(
        FunctionName=Config.PDF_LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"html": html_content, "fileName": file_name}),
    )
    payload = json.loads(response["Payload"].read())
    body = payload.get("body")
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or "url" not in body:
        raise ValueError("Invalid Lambda response for PDF generation")
    return str(body["url"])


async def generate_pdf_via_lambda(html_content: str, file_name: str) -> str:
    return await asyncio.to_thread(_invoke_lambda, html_content, file_name)
