from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "market_data_mode" in body


def test_ready_returns_components() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert "components" in body
    assert "api" in body["components"]


def test_root_mentions_attention_engine() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "attention" in response.json()["message"].lower()
