from __future__ import annotations

import asyncio
import json

import boto3

from app.core.config import Config


def _build_sqs_client():
    client_kwargs: dict[str, str] = {}
    if Config.AWS_REGION:
        client_kwargs["region_name"] = Config.AWS_REGION
    if Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_KEY
    return boto3.client("sqs", **client_kwargs)


def _send_event(event_data: dict, deduplication_id: str | None = None) -> None:
    if not Config.BOOKING_PAYMENT_QUEUE_URL:
        raise ValueError("BOOKING_PAYMENT_QUEUE_URL is not configured")

    try:
        sqs = _build_sqs_client()
        message = {
            "QueueUrl": Config.BOOKING_PAYMENT_QUEUE_URL,
            "MessageBody": json.dumps(event_data),
        }
        print(f"[event_publisher] send_message")
        if Config.BOOKING_PAYMENT_QUEUE_URL.endswith(".fifo"):
            message["MessageGroupId"] = "booking-events"
            message["MessageDeduplicationId"] = str(
                deduplication_id or event_data.get("payment_transaction_id")
            )
        sqs.send_message(**message)
    except Exception as exc:
        print(f"[event_publisher] send_message failed: {exc}, event_data={event_data}")
        raise


async def publish_payment_success_event(event_data: dict) -> None:
    await asyncio.to_thread(
        _send_event, event_data, str(event_data.get("payment_transaction_id"))
    )


async def publish_payment_failed_event(event_data: dict) -> None:
    await asyncio.to_thread(
        _send_event, event_data, str(event_data.get("payment_transaction_id"))
    )


async def publish_refund_processed_event(event_data: dict) -> None:
    await asyncio.to_thread(_send_event, event_data, str(event_data.get("refund_id")))


async def publish_refund_failed_event(event_data: dict) -> None:
    await asyncio.to_thread(_send_event, event_data, str(event_data.get("refund_id")))
