"""API-layer tests for the read-only /exercises endpoints."""


def test_list_exercises(client, auth_headers, test_exercise):
    response = client.get("/exercises", headers=auth_headers)
    assert response.status_code == 200
    names = [e["name"] for e in response.json()]
    assert names == [test_exercise.name]


def test_get_exercise(client, auth_headers, test_exercise):
    response = client.get(f"/exercises/{test_exercise.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == test_exercise.id


def test_get_nonexistent_exercise_returns_404(client, auth_headers):
    response = client.get("/exercises/999", headers=auth_headers)
    assert response.status_code == 404


def test_exercises_endpoints_require_authentication(client, test_exercise):
    assert client.get("/exercises").status_code == 401
    assert client.get(f"/exercises/{test_exercise.id}").status_code == 401
