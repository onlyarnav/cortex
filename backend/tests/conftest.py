import pytest
from fastapi.testclient import TestClient

from main import app

TEST_EMAIL = "test_user_1@example.com"
TEST_PASSWORD = "testpass123"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_token(client):
    client.post("/auth/signup", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    response = client.post(
        "/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    return response.json()["access_token"]