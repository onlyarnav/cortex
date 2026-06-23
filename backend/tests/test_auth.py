def test_signup_duplicate_email_fails(client, auth_token):
    response = client.post(
        "/auth/signup",
        json={"email": "test_user_1@example.com", "password": "testpass123"},
    )
    assert response.status_code == 400


def test_login_wrong_password_fails(client):
    response = client.post(
        "/auth/login",
        data={"username": "test_user_1@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_login_success(client, auth_token):
    assert auth_token is not None