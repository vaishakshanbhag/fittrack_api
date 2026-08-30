"""API-layer tests for the /workouts CRUD endpoints."""


def _payload(exercise_id, **overrides):
    data = {
        "exercise_id": exercise_id,
        "duration_minutes": 30,
        "calories_burned": 250,
        "date": "2026-01-01",
        "notes": None,
    }
    data.update(overrides)
    return data


def test_create_workout(client, auth_headers, test_exercise):
    response = client.post("/workouts", json=_payload(test_exercise.id), headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["exercise_id"] == test_exercise.id
    assert body["user_id"] is not None


def test_list_workouts_scoped_to_current_user(
    client, auth_headers, other_auth_headers, test_exercise
):
    client.post(
        "/workouts", json=_payload(test_exercise.id, notes="Mine"), headers=auth_headers
    )
    client.post(
        "/workouts", json=_payload(test_exercise.id, notes="Theirs"), headers=other_auth_headers
    )

    response = client.get("/workouts", headers=auth_headers)
    assert response.status_code == 200
    notes = [w["notes"] for w in response.json()]
    assert notes == ["Mine"]


def test_get_workout(client, auth_headers, test_exercise):
    created = client.post(
        "/workouts", json=_payload(test_exercise.id), headers=auth_headers
    ).json()
    response = client.get(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_workout_returns_404(client, auth_headers):
    response = client.get("/workouts/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_other_users_workout_returns_404(
    client, auth_headers, other_auth_headers, test_exercise
):
    created = client.post(
        "/workouts", json=_payload(test_exercise.id), headers=other_auth_headers
    ).json()
    response = client.get(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_update_workout(client, auth_headers, test_exercise):
    created = client.post(
        "/workouts", json=_payload(test_exercise.id), headers=auth_headers
    ).json()
    updated_payload = _payload(test_exercise.id, notes="Updated Run")
    response = client.put(f"/workouts/{created['id']}", json=updated_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["notes"] == "Updated Run"


def test_update_nonexistent_workout_returns_404(client, auth_headers, test_exercise):
    response = client.put(
        "/workouts/999", json=_payload(test_exercise.id), headers=auth_headers
    )
    assert response.status_code == 404


def test_update_other_users_workout_returns_404(
    client, auth_headers, other_auth_headers, test_exercise
):
    created = client.post(
        "/workouts", json=_payload(test_exercise.id), headers=other_auth_headers
    ).json()
    response = client.put(
        f"/workouts/{created['id']}", json=_payload(test_exercise.id), headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_workout(client, auth_headers, test_exercise):
    created = client.post(
        "/workouts", json=_payload(test_exercise.id), headers=auth_headers
    ).json()
    response = client.delete(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    follow_up = client.get(f"/workouts/{created['id']}", headers=auth_headers)
    assert follow_up.status_code == 404


def test_delete_nonexistent_workout_returns_404(client, auth_headers):
    response = client.delete("/workouts/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_other_users_workout_returns_404(
    client, auth_headers, other_auth_headers, test_exercise
):
    created = client.post(
        "/workouts", json=_payload(test_exercise.id), headers=other_auth_headers
    ).json()
    response = client.delete(f"/workouts/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_create_workout_invalid_duration_returns_422(client, auth_headers, test_exercise):
    response = client.post(
        "/workouts",
        json=_payload(test_exercise.id, duration_minutes=0),
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_workouts_endpoints_require_authentication(client, test_exercise):
    assert client.get("/workouts").status_code == 401
    assert client.post("/workouts", json=_payload(test_exercise.id)).status_code == 401
