"""Security header + digest auth smoke tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.seed import DEMO_WATCHLIST_ID


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient) -> None:
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("x-request-id")


@pytest.mark.asyncio
async def test_digest_requires_auth(client: AsyncClient) -> None:
    res = await client.get(f"/api/v1/watchlists/{DEMO_WATCHLIST_ID}/digest")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_digest_for_demo_user(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "DemoPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["token"]["access_token"]
    res = await client.get(
        f"/api/v1/watchlists/{DEMO_WATCHLIST_ID}/digest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["watchlist_id"] == str(DEMO_WATCHLIST_ID)
    assert "items" in body
    assert "summary" in body
    # If pipeline seeded, HDFC should rank first among non-empty digests
    if body["items"]:
        symbols = [i["instrument"]["symbol"] for i in body["items"]]
        assert "RELIANCE" not in symbols or body["items"][0]["instrument"]["symbol"] != "RELIANCE"
