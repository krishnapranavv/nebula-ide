"""
S3 storage service for project files.
Bucket is always private — no public access.
All reads go through presigned URLs (short-lived, authenticated).
"""
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _client():
    kwargs: dict = {"region_name": settings.AWS_REGION}
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


async def ensure_bucket():
    """Idempotent bucket creation with public access fully blocked."""
    client = _client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
        logger.debug(f"Bucket {settings.S3_BUCKET} already exists")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            client.create_bucket(Bucket=settings.S3_BUCKET)
            client.put_public_access_block(
                Bucket=settings.S3_BUCKET,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            logger.info(f"Created private S3 bucket: {settings.S3_BUCKET}")
        else:
            raise


async def upload_text(s3_key: str, content: str) -> int:
    """Upload UTF-8 text content. Returns byte size stored."""
    client = _client()
    data = content.encode("utf-8")
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=s3_key,
        Body=data,
        ContentType="text/plain; charset=utf-8",
        ServerSideEncryption="AES256",
    )
    return len(data)


async def download_text(s3_key: str) -> str:
    """Download and decode UTF-8 text. Returns empty string if not found."""
    client = _client()
    try:
        resp = client.get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
        return resp["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return ""
        raise


async def delete_object(s3_key: str):
    client = _client()
    try:
        client.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
    except ClientError as e:
        logger.warning(f"S3 delete failed for key {s3_key}: {e}")


async def delete_prefix(prefix: str):
    """Bulk-delete all objects under a prefix (used for project deletion)."""
    client = _client()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
        objects = page.get("Contents", [])
        if objects:
            client.delete_objects(
                Bucket=settings.S3_BUCKET,
                Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
            )
    logger.info(f"Deleted all objects under prefix: {prefix}")


async def presigned_url(s3_key: str, expires: int = 3600) -> str:
    client = _client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
        ExpiresIn=expires,
    )
