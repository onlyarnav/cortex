from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_signup():
    response = client.post("/auth/signup", json={
        "email": "test_user_1@example.com",
        "password": "testpass123"
    })
    assert response.status_code in (200, 400)  # 400 if already exists

def test_login():
    response = client.post("/auth/login", data={
        "username": "test_user_1@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()