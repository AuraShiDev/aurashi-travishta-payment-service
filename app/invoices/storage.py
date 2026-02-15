from __future__ import annotations

import boto3

from app.core.config import Config


def upload_to_s3(file_path: str, key: str) -> str:
    if not (Config.AWS_ACCESS_KEY and Config.AWS_SECRET_KEY and Config.AWS_REGION and Config.S3_BUCKET):
        raise ValueError("AWS S3 configuration is incomplete")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=Config.AWS_ACCESS_KEY,
        aws_secret_access_key=Config.AWS_SECRET_KEY,
        region_name=Config.AWS_REGION,
    )
    s3.upload_file(file_path, Config.S3_BUCKET, key)
    return f"https://{Config.S3_BUCKET}.s3.amazonaws.com/{key}"
