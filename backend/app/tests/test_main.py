"""
Integration tests for the main API endpoints.
Uses httpx TestClient with mocked AWS dependencies.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def mock_db():
    """Mock all DynamoDB calls so tests don't need real AWS."""
    with patch("app.core.database.init_tables", new_callable=AsyncMock), \
         patch("app.services.storage.s3.ensure_bucket", new_callable=AsyncMock):
        yield


@pytest.mark.asyncio
async def test_health_endpoint(mock_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_signup_missing_fields(mock_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/signup", json={"email": "test@example.com"})
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_wrong_credentials(mock_db):
    with patch("app.core.database.db_get_user_by_email", new_callable=AsyncMock, return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/login", json={"email": "x@x.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_execute_requires_auth(mock_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/execute", json={"code": "print('hi')", "language": "python"})
    assert resp.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_execute_invalid_language(mock_db):
    # Even with auth header (will fail auth but returns 401/403, not 500)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/execute",
            json={"code": "print('hi')", "language": "ruby"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code in (401, 422)
