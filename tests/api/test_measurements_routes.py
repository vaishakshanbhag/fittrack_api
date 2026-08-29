"""API-layer tests for the /measurements CRUD endpoints."""

MEASUREMENT_PAYLOAD = {
    "height_cm": 180.0,
    "weight_kg": 75.0,
    "chest_cm": 100.0,
    "waist_cm": 85.0,
    "hip_cm": 95.0,
    "thigh_cm": 55.0,
    "calf_cm": 38.0,
    "arm_cm": 32.0,
    "forearm_cm": 27.0,
    "recorded_at": "2026-01-01T08:00:00",
}


def test_create_measurement(client, auth_headers):
    response = client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["height_cm"] == 180.0
    assert body["user_id"] is not None


def test_create_measurement_includes_bmi(client, auth_headers):
    response = client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    # height_cm=180.0, weight_kg=75.0: 75 / 1.8**2 = 23.148... -> 23.1
    assert body["bmi"] == 23.1


def test_get_measurement_includes_bmi(client, auth_headers):
    created = client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers).json()
    response = client.get(f"/measurements/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["bmi"] == 23.1


def test_list_measurements_scoped_to_current_user(client, auth_headers, other_auth_headers):
    client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers)
    client.post(
        "/measurements",
        json={**MEASUREMENT_PAYLOAD, "weight_kg": 90.0},
        headers=other_auth_headers,
    )

    response = client.get("/measurements", headers=auth_headers)
    assert response.status_code == 200
    weights = [m["weight_kg"] for m in response.json()]
    assert weights == [75.0]


def test_get_measurement(client, auth_headers):
    created = client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers).json()
    response = client.get(f"/measurements/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_measurement_returns_404(client, auth_headers):
    response = client.get("/measurements/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_other_users_measurement_returns_404(client, auth_headers, other_auth_headers):
    created = client.post(
        "/measurements", json=MEASUREMENT_PAYLOAD, headers=other_auth_headers
    ).json()
    response = client.get(f"/measurements/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_update_measurement(client, auth_headers):
    created = client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers).json()
    updated_payload = {**MEASUREMENT_PAYLOAD, "weight_kg": 72.5}
    response = client.put(
        f"/measurements/{created['id']}", json=updated_payload, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["weight_kg"] == 72.5


def test_update_nonexistent_measurement_returns_404(client, auth_headers):
    response = client.put("/measurements/999", json=MEASUREMENT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 404


def test_update_other_users_measurement_returns_404(client, auth_headers, other_auth_headers):
    created = client.post(
        "/measurements", json=MEASUREMENT_PAYLOAD, headers=other_auth_headers
    ).json()
    response = client.put(
        f"/measurements/{created['id']}", json=MEASUREMENT_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_measurement(client, auth_headers):
    created = client.post("/measurements", json=MEASUREMENT_PAYLOAD, headers=auth_headers).json()
    response = client.delete(f"/measurements/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    follow_up = client.get(f"/measurements/{created['id']}", headers=auth_headers)
    assert follow_up.status_code == 404


def test_delete_nonexistent_measurement_returns_404(client, auth_headers):
    response = client.delete("/measurements/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_other_users_measurement_returns_404(client, auth_headers, other_auth_headers):
    created = client.post(
        "/measurements", json=MEASUREMENT_PAYLOAD, headers=other_auth_headers
    ).json()
    response = client.delete(f"/measurements/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_create_measurement_invalid_weight_returns_422(client, auth_headers):
    response = client.post(
        "/measurements", json={**MEASUREMENT_PAYLOAD, "weight_kg": 0}, headers=auth_headers
    )
    assert response.status_code == 422


def test_measurements_endpoints_require_authentication(client):
    assert client.get("/measurements").status_code == 401
    assert client.post("/measurements", json=MEASUREMENT_PAYLOAD).status_code == 401
