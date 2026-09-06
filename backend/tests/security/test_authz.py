"""Security tests: auth required, IDOR closed, invalid credentials."""

import uuid

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
async def test_unauthenticated_watchlists_rejected(client: AsyncClient) -> None:
    res = await client.get("/api/v1/watchlists")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_demo_and_list_watchlists(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "DemoPass123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    watchlists = await client.get("/api/v1/watchlists", headers=headers)
    assert watchlists.status_code == 200
    body = watchlists.json()
    assert len(body) >= 1
    ids = {row["watchlist_id"] for row in body}
    assert str(DEMO_WATCHLIST_ID) in ids


@pytest.mark.asyncio
async def test_idor_other_users_watchlist_not_found(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "DemoPass123!"},
    )
    token = login.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = uuid.uuid4()
    res = await client.get(f"/api/v1/watchlists/{fake_id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "WATCHLIST_NOT_FOUND"


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "wrong-password"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_instrument_search(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "DemoPass123!"},
    )
    token = login.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/v1/instruments/search", params={"q": "hdfc"}, headers=headers)
    assert res.status_code == 200
    symbols = [row["symbol"] for row in res.json()]
    assert "HDFCBANK" in symbols
