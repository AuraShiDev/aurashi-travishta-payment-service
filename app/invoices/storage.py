from __future__ import annotations

import boto3
from urllib.parse import urlparse

from app.core.config import Config


def _build_s3_client():
    client_kwargs: dict[str, str] = {}
    if Config.AWS_REGION:
        client_kwargs["region_name"] = Config.AWS_REGION
    if Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_KEY
    return boto3.client("s3", **client_kwargs)


def _extract_bucket_key_from_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    host_parts = parsed.netloc.split(".")
    path = parsed.path.lstrip("/")

    # Virtual-hosted-style: https://bucket.s3.amazonaws.com/key
    if len(host_parts) >= 3 and host_parts[1] == "s3":
        bucket = host_parts[0]
        key = path
        if bucket and key:
            return bucket, key

    # Path-style: https://s3.amazonaws.com/bucket/key or regional variant
    if host_parts and host_parts[0] == "s3":
        path_parts = path.split("/", 1)
        if len(path_parts) == 2 and path_parts[0] and path_parts[1]:
            return path_parts[0], path_parts[1]

    raise ValueError("Unsupported S3 URL format")


def upload_to_s3(file_path: str, key: str) -> str:
    if not (Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY and Config.AWS_REGION and Config.S3_BUCKET):
        raise ValueError("AWS S3 configuration is incomplete")

    s3 = _build_s3_client()
    s3.upload_file(file_path, Config.S3_BUCKET, key)
    return f"https://{Config.S3_BUCKET}.s3.amazonaws.com/{key}"


def generate_presigned_url_from_s3_url(url: str, expires_in: int = 3600) -> str:
    bucket, key = _extract_bucket_key_from_url(url)
    return _build_s3_client().generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
