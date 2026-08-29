"""API-layer tests for the /journal_entries CRUD endpoints."""

JOURNAL_ENTRY_PAYLOAD = {
    "title": "Reflections",
    "content": "Felt strong during today's workout.",
    "mood": "motivated",
    "entry_date": "2026-01-01",
}


def test_create_journal_entry(client, auth_headers):
    response = client.post("/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Reflections"
    assert body["user_id"] is not None


def test_list_journal_entries_scoped_to_current_user(client, auth_headers, other_auth_headers):
    client.post("/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers)
    client.post(
        "/journal_entries",
        json={**JOURNAL_ENTRY_PAYLOAD, "title": "Theirs"},
        headers=other_auth_headers,
    )

    response = client.get("/journal_entries", headers=auth_headers)
    assert response.status_code == 200
    titles = [e["title"] for e in response.json()]
    assert titles == ["Reflections"]


def test_get_journal_entry(client, auth_headers):
    created = client.post(
        "/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers
    ).json()
    response = client.get(f"/journal_entries/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_journal_entry_returns_404(client, auth_headers):
    response = client.get("/journal_entries/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_other_users_journal_entry_returns_404(client, auth_headers, other_auth_headers):
    created = client.post(
        "/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=other_auth_headers
    ).json()
    response = client.get(f"/journal_entries/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_update_journal_entry(client, auth_headers):
    created = client.post(
        "/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers
    ).json()
    updated_payload = {**JOURNAL_ENTRY_PAYLOAD, "title": "Updated Entry"}
    response = client.put(
        f"/journal_entries/{created['id']}", json=updated_payload, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Entry"


def test_update_nonexistent_journal_entry_returns_404(client, auth_headers):
    response = client.put(
        "/journal_entries/999", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 404


def test_update_other_users_journal_entry_returns_404(client, auth_headers, other_auth_headers):
    created = client.post(
        "/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=other_auth_headers
    ).json()
    response = client.put(
        f"/journal_entries/{created['id']}", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_journal_entry(client, auth_headers):
    created = client.post(
        "/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=auth_headers
    ).json()
    response = client.delete(f"/journal_entries/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    follow_up = client.get(f"/journal_entries/{created['id']}", headers=auth_headers)
    assert follow_up.status_code == 404


def test_delete_nonexistent_journal_entry_returns_404(client, auth_headers):
    response = client.delete("/journal_entries/999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_other_users_journal_entry_returns_404(client, auth_headers, other_auth_headers):
    created = client.post(
        "/journal_entries", json=JOURNAL_ENTRY_PAYLOAD, headers=other_auth_headers
    ).json()
    response = client.delete(f"/journal_entries/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_create_journal_entry_invalid_title_returns_422(client, auth_headers):
    response = client.post(
        "/journal_entries", json={**JOURNAL_ENTRY_PAYLOAD, "title": ""}, headers=auth_headers
    )
    assert response.status_code == 422


def test_journal_entries_endpoints_require_authentication(client):
    assert client.get("/journal_entries").status_code == 401
    assert client.post("/journal_entries", json=JOURNAL_ENTRY_PAYLOAD).status_code == 401
