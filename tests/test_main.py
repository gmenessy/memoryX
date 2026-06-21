"""
Basic tests for FastAPI Application
"""
from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint():
    """
    Test the root endpoint returns basic application information.
    """
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "application" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


def test_health_check():
    """
    Test the health check endpoint returns healthy status.
    """
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "application" in data
    assert "version" in data


def test_api_info():
    """
    Test the API info endpoint returns system configuration.
    """
    client = TestClient(app)
    response = client.get("/api/info")

    assert response.status_code == 200
    data = response.json()

    assert "application" in data
    assert "version" in data
    assert "debug" in data
    assert "database" in data
    assert "log_level" in data


def test_404_handler():
    """
    Test that non-existent endpoints return 404.
    """
    client = TestClient(app)
    response = client.get("/non-existent-endpoint")

    assert response.status_code == 404