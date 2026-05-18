"""
DynamoDB data layer.
Uses PAY_PER_REQUEST billing — no provisioned capacity cost when idle.
All tables created with GSIs to support the required access patterns.
"""
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from app.core.config import settings
import logging
import uuid
from datetime import datetime, timezone, date

logger = logging.getLogger(__name__)


# ── Client factory ────────────────────────────────────────────────────────────

def _resource():
    kwargs: dict = {"region_name": settings.AWS_REGION}
    if settings.DYNAMODB_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.DYNAMODB_ENDPOINT_URL
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.resource("dynamodb", **kwargs)


def _client():
    kwargs: dict = {"region_name": settings.AWS_REGION}
    if settings.DYNAMODB_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.DYNAMODB_ENDPOINT_URL
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("dynamodb", **kwargs)


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ── Table bootstrap ───────────────────────────────────────────────────────────

TABLE_DEFINITIONS = [
    {
        "TableName": settings.TABLE_USERS,
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
        "TableName": settings.TABLE_PROJECTS,
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
        "TableName": settings.TABLE_FILES,
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
        "TableName": settings.TABLE_EXECUTIONS,
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
        "TableName": settings.TABLE_REVIEWS,
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


async def init_tables():
    client = _client()
    for defn in TABLE_DEFINITIONS:
        try:
            client.create_table(**defn)
            logger.info(f"Created DynamoDB table: {defn['TableName']}")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ResourceInUseException":
                logger.debug(f"Table already exists: {defn['TableName']}")
            else:
                logger.error(f"Failed to create table {defn['TableName']}: {e}")
                raise


# ── Users ─────────────────────────────────────────────────────────────────────

async def db_create_user(email: str, username: str, password_hash: str) -> dict:
    table = _resource().Table(settings.TABLE_USERS)
    user = {
        "user_id":       _new_id(),
        "email":         email,
        "username":      username,
        "password_hash": password_hash,
        "role":          "user",
        "created_at":    _now(),
        "last_login":    _now(),
    }
    table.put_item(Item=user)
    return user


async def db_get_user_by_email(email: str) -> dict | None:
    table = _resource().Table(settings.TABLE_USERS)
    resp = table.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
    )
    items = resp.get("Items", [])
    return items[0] if items else None


async def db_get_user_by_id(user_id: str) -> dict | None:
    table = _resource().Table(settings.TABLE_USERS)
    resp = table.get_item(Key={"user_id": user_id})
    return resp.get("Item")


async def db_update_last_login(user_id: str):
    table = _resource().Table(settings.TABLE_USERS)
    table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET last_login = :t",
        ExpressionAttributeValues={":t": _now()},
    )


# ── Projects ──────────────────────────────────────────────────────────────────

async def db_create_project(user_id: str, name: str, language: str, description: str) -> dict:
    table = _resource().Table(settings.TABLE_PROJECTS)
    project_id = _new_id()
    project = {
        "project_id":  project_id,
        "user_id":     user_id,
        "name":        name,
        "language":    language,
        "description": description,
        "s3_prefix":   f"projects/{user_id}/{project_id}/",
        "created_at":  _now(),
        "updated_at":  _now(),
    }
    table.put_item(Item=project)
    return project


async def db_list_projects(user_id: str) -> list:
    table = _resource().Table(settings.TABLE_PROJECTS)
    resp = table.query(
        IndexName="user-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
    )
    return sorted(resp.get("Items", []), key=lambda x: x.get("updated_at", ""), reverse=True)


async def db_get_project(project_id: str) -> dict | None:
    table = _resource().Table(settings.TABLE_PROJECTS)
    resp = table.get_item(Key={"project_id": project_id})
    return resp.get("Item")


async def db_update_project(project_id: str, **kwargs) -> dict | None:
    table = _resource().Table(settings.TABLE_PROJECTS)
    kwargs["updated_at"] = _now()
    expr = "SET " + ", ".join(f"#k{i} = :v{i}" for i, k in enumerate(kwargs))
    names = {f"#k{i}": k for i, k in enumerate(kwargs)}
    values = {f":v{i}": v for i, v in enumerate(kwargs.values())}
    resp = table.update_item(
        Key={"project_id": project_id},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes")


async def db_delete_project(project_id: str):
    table = _resource().Table(settings.TABLE_PROJECTS)
    table.delete_item(Key={"project_id": project_id})


# ── Files ─────────────────────────────────────────────────────────────────────

async def db_create_file(project_id: str, filename: str, s3_key: str, size_bytes: int) -> dict:
    table = _resource().Table(settings.TABLE_FILES)
    record = {
        "file_id":    _new_id(),
        "project_id": project_id,
        "filename":   filename,
        "s3_key":     s3_key,
        "size_bytes": size_bytes,
        "updated_at": _now(),
    }
    table.put_item(Item=record)
    return record


async def db_list_files(project_id: str) -> list:
    table = _resource().Table(settings.TABLE_FILES)
    resp = table.query(
        IndexName="project-index",
        KeyConditionExpression=Key("project_id").eq(project_id),
    )
    return sorted(resp.get("Items", []), key=lambda x: x.get("filename", ""))


async def db_get_file(file_id: str) -> dict | None:
    table = _resource().Table(settings.TABLE_FILES)
    resp = table.get_item(Key={"file_id": file_id})
    return resp.get("Item")


async def db_update_file(file_id: str, s3_key: str, size_bytes: int):
    table = _resource().Table(settings.TABLE_FILES)
    table.update_item(
        Key={"file_id": file_id},
        UpdateExpression="SET s3_key = :s, size_bytes = :z, updated_at = :t",
        ExpressionAttributeValues={":s": s3_key, ":z": size_bytes, ":t": _now()},
    )


async def db_delete_file(file_id: str):
    table = _resource().Table(settings.TABLE_FILES)
    table.delete_item(Key={"file_id": file_id})


# ── Executions ────────────────────────────────────────────────────────────────

async def db_save_execution(data: dict) -> dict:
    table = _resource().Table(settings.TABLE_EXECUTIONS)
    table.put_item(Item=data)
    return data


async def db_list_executions(user_id: str, limit: int = 20) -> list:
    table = _resource().Table(settings.TABLE_EXECUTIONS)
    resp = table.query(
        IndexName="user-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
        ScanIndexForward=False,
        Limit=limit,
    )
    return resp.get("Items", [])


# ── Reviews ───────────────────────────────────────────────────────────────────

async def db_save_review(data: dict) -> dict:
    table = _resource().Table(settings.TABLE_REVIEWS)
    table.put_item(Item=data)
    return data


async def db_get_daily_review_count(user_id: str) -> int:
    today = date.today().isoformat()
    table = _resource().Table(settings.TABLE_REVIEWS)
    resp = table.query(
        IndexName="user-index",
        KeyConditionExpression=Key("user_id").eq(user_id),
        FilterExpression="begins_with(reviewed_at, :d)",
        ExpressionAttributeValues={":d": today},
    )
    return len(resp.get("Items", []))
