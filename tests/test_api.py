"""
API tests for FastAPI endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import initialize_database
from backend.schema_engine import schema_engine


@pytest.fixture(scope="module")
def client():
    initialize_database()
    schema_engine.introspect_schema(force_refresh=True)
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "dialect" in data


def test_schema_endpoint(client):
    response = client.get("/api/schema")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    assert "customers" in data["tables"]


def test_sample_queries_endpoint(client):
    response = client.get("/api/sample-queries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


def test_validate_safe_query(client):
    response = client.post("/api/validate", json={"sql": "SELECT id, name FROM categories"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "valid"


def test_validate_blocked_query(client):
    response = client.post("/api/validate", json={"sql": "DELETE FROM categories"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid"


def test_query_endpoint(client):
    response = client.post("/api/query", json={
        "query": "Show the top 5 customers by total spending",
        "enforce_validation": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "sanitized_sql" in data
    assert "execution" in data
