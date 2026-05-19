#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# LocalStack initialisation script
# Runs automatically when LocalStack starts (via docker-compose volume mount)
# Creates S3 bucket and any other local AWS resources needed for dev
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BUCKET="nebula-ide-projects"
REGION="us-east-1"

echo "▶ Initialising LocalStack resources..."

# Wait for LocalStack S3 to be ready
until awslocal s3 ls &>/dev/null; do
  echo "  Waiting for LocalStack S3..."
  sleep 1
done

# Create S3 bucket
if awslocal s3 ls "s3://${BUCKET}" 2>/dev/null; then
  echo "  ~ S3 bucket already exists: ${BUCKET}"
else
  awslocal s3 mb "s3://${BUCKET}" --region "${REGION}"
  echo "  ✓ S3 bucket created: ${BUCKET}"
fi

echo "▶ LocalStack ready. Resources initialised."
echo ""
echo "  S3:       http://localhost:4566"
echo "  DynamoDB: http://localhost:8000"
echo ""