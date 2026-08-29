"""API-layer tests for the /workouts CRUD endpoints."""

WORKOUT_PAYLOAD = {
    "name": "Morning Run",
    "type": "cardio",
    "duration_minutes": 30,
    "calories_burned": 250,
    "date": "2026-01-01",
    "notes": None,
}


def test_create_workout(client, auth_headers):
    response = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Morning Run"
    assert body["user_id"] is not None


def test_list_workouts_scoped_to_current_user(client, auth_headers, other_auth_headers):
    client.post("/workouts", json=WORKOUT_PAYLOAD, headers=auth_headers)
    client.post("/workouts", json={**WORKOUT_PAYLOAD, "name": "Theirs"}, headers=other_auth_headers)

    response = client.get("/workouts", headers=auth_headers)
    assert response.status_code == 200
    names = [w["name"] for w in response.json()]
    assert names == ["Morning Run"]


def test_get_workout(client, auth_headers):
    created = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=auth_headers).json()
    response = client.get(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_workout_returns_404(client, auth_headers):
    response = client.get("/workouts/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_other_users_workout_returns_404(client, auth_headers, other_auth_headers):
    created = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=other_auth_headers).json()
    response = client.get(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_update_workout(client, auth_headers):
    created = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=auth_headers).json()
    updated_payload = {**WORKOUT_PAYLOAD, "name": "Updated Run"}
    response = client.put(f"/workouts/{created['id']}", json=updated_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Run"


def test_update_nonexistent_workout_returns_404(client, auth_headers):
    response = client.put("/workouts/999", json=WORKOUT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 404


def test_update_other_users_workout_returns_404(client, auth_headers, other_auth_headers):
    created = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=other_auth_headers).json()
    response = client.put(f"/workouts/{created['id']}", json=WORKOUT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 404


def test_delete_workout(client, auth_headers):
    created = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=auth_headers).json()
    response = client.delete(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    follow_up = client.get(f"/workouts/{created['id']}", headers=auth_headers)
    assert follow_up.status_code == 404


def test_delete_nonexistent_workout_returns_404(client, auth_headers):
    response = client.delete("/workouts/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_other_users_workout_returns_404(client, auth_headers, other_auth_headers):
    created = client.post("/workouts", json=WORKOUT_PAYLOAD, headers=other_auth_headers).json()
    response = client.delete(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_create_workout_invalid_duration_returns_422(client, auth_headers):
    response = client.post(
        "/workouts", json={**WORKOUT_PAYLOAD, "duration_minutes": 0}, headers=auth_headers
    )
    assert response.status_code == 422


def test_workouts_endpoints_require_authentication(client):
    assert client.get("/workouts").status_code == 401
    assert client.post("/workouts", json=WORKOUT_PAYLOAD).status_code == 401
