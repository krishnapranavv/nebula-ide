#!/usr/bin/env python3
"""
Create all DynamoDB tables for Nebula IDE.
Works with both local DynamoDB (http://localhost:8000) and real AWS.

Usage:
  # Local dev (with docker-compose running)
  python setup_dynamodb.py --endpoint http://localhost:8000

  # Real AWS (uses ~/.aws credentials or EC2 instance role)
  python setup_dynamodb.py
"""
import boto3
import argparse
import sys
from botocore.exceptions import ClientError

TABLES = [
    {
        "TableName": "nebula_users",
        "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "email",   "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [{
            "IndexName": "email-index",
            "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "nebula_projects",
        "KeySchema": [{"AttributeName": "project_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "user_id",    "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [{
            "IndexName": "user-index",
            "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "nebula_files",
        "KeySchema": [{"AttributeName": "file_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "file_id",    "AttributeType": "S"},
            {"AttributeName": "project_id", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [{
            "IndexName": "project-index",
            "KeySchema": [{"AttributeName": "project_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "nebula_executions",
        "KeySchema": [{"AttributeName": "exec_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "exec_id",  "AttributeType": "S"},
            {"AttributeName": "user_id",  "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [{
            "IndexName": "user-index",
            "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "nebula_reviews",
        "KeySchema": [{"AttributeName": "review_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "review_id", "AttributeType": "S"},
            {"AttributeName": "user_id",   "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [{
            "IndexName": "user-index",
            "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def create_tables(endpoint: str | None = None):
    kwargs = {"region_name": "us-east-1"}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        kwargs["aws_access_key_id"] = "local"
        kwargs["aws_secret_access_key"] = "local"

    client = boto3.client("dynamodb", **kwargs)

    for table in TABLES:
        try:
            client.create_table(**table)
            print(f"  ✓ Created: {table['TableName']}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"  ~ Exists:  {table['TableName']}")
            else:
                print(f"  ✗ Error:   {table['TableName']} — {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Nebula IDE DynamoDB tables")
    parser.add_argument("--endpoint", help="DynamoDB endpoint URL (e.g. http://localhost:8000)")
    args = parser.parse_args()

    target = f" ({args.endpoint})" if args.endpoint else " (AWS)"
    print(f"Setting up DynamoDB tables{target}...")
    create_tables(args.endpoint)
    print("Done.")