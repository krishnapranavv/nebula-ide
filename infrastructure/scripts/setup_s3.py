#!/usr/bin/env python3
"""
Create and configure the Nebula IDE S3 bucket.
Works with LocalStack (local dev) and real AWS.

Usage:
  # Local dev
  python setup_s3.py --endpoint http://localhost:4566

  # Real AWS
  python setup_s3.py --bucket my-nebula-ide-projects
"""
import boto3
import argparse
import sys
from botocore.exceptions import ClientError

DEFAULT_BUCKET = "nebula-ide-projects"
REGION         = "us-east-1"


def setup_bucket(bucket: str, endpoint: str | None, region: str):
    kwargs: dict = {"region_name": region}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        kwargs["aws_access_key_id"] = "local"
        kwargs["aws_secret_access_key"] = "local"

    s3 = boto3.client("s3", **kwargs)

    # ── Create bucket ─────────────────────────────────────────────────────────
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"  ✓ Created bucket: {bucket}")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"  ~ Bucket exists: {bucket}")
        else:
            print(f"  ✗ Create failed: {e}", file=sys.stderr)
            sys.exit(1)

    # ── Block all public access (skip for LocalStack — not supported) ─────────
    if not endpoint:
        try:
            s3.put_public_access_block(
                Bucket=bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls":       True,
                    "IgnorePublicAcls":      True,
                    "BlockPublicPolicy":     True,
                    "RestrictPublicBuckets": True,
                },
            )
            print("  ✓ Public access blocked")
        except ClientError as e:
            print(f"  ! Could not block public access: {e}", file=sys.stderr)

    # ── Enable versioning (optional, off by default to save cost) ────────────
    # Uncomment to enable project file version history:
    # s3.put_bucket_versioning(
    #     Bucket=bucket,
    #     VersioningConfiguration={"Status": "Enabled"},
    # )
    # print("  ✓ Versioning enabled")

    # ── Lifecycle rule: auto-delete temp execution files after 1 day ─────────
    try:
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration={
                "Rules": [
                    {
                        "ID":     "delete-temp-exec-files",
                        "Status": "Enabled",
                        "Filter": {"Prefix": "tmp/"},
                        "Expiration": {"Days": 1},
                    }
                ]
            },
        )
        print("  ✓ Lifecycle rule set (tmp/ deleted after 1 day)")
    except ClientError as e:
        print(f"  ! Lifecycle rule skipped: {e}", file=sys.stderr)

    print(f"\nBucket ready: s3://{bucket}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up Nebula IDE S3 bucket")
    parser.add_argument("--bucket",   default=DEFAULT_BUCKET, help="Bucket name")
    parser.add_argument("--endpoint", default=None,           help="Custom S3 endpoint (e.g. http://localhost:4566)")
    parser.add_argument("--region",   default=REGION,         help="AWS region")
    args = parser.parse_args()

    target = f" ({args.endpoint})" if args.endpoint else " (AWS)"
    print(f"Setting up S3 bucket{target}...")
    setup_bucket(args.bucket, args.endpoint, args.region)