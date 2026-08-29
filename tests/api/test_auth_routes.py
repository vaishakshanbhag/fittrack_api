"""API-layer tests for /auth/signup, /auth/login, and the auth guard."""


def test_signup_returns_created_user_without_password_hash(client):
    response = client.post("/auth/signup", json={"email": "new@example.com", "password": "password123"})
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_signup_duplicate_email_returns_409(client):
    client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    response = client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert response.status_code == 409


def test_login_success_returns_token(client):
    client.post("/auth/signup", json={"email": "login@example.com", "password": "password123"})
    response = client.post(
        "/auth/login", data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_returns_401(client):
    client.post("/auth/signup", json={"email": "login2@example.com", "password": "password123"})
    response = client.post(
        "/auth/login", data={"username": "login2@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "password123"}
    )
    assert response.status_code == 401


def test_protected_route_without_token_returns_401(client):
    response = client.get("/workouts")
    assert response.status_code == 401


def test_protected_route_with_malformed_token_returns_401(client):
    response = client.get("/workouts", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401
