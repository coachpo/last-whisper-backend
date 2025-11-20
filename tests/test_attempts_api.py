"""Integration tests for attempts API routes."""

from app.models.models import Item


def _create_item(db_manager, *, locale="en-US", text="sample") -> Item:
    with db_manager.get_session() as session:
        item = Item(locale=locale, text=text, difficulty=1)
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


def test_create_attempt_endpoint_returns_created_attempt(test_client, db_manager):
    item = _create_item(db_manager, text="Hello world")

    response = test_client.post(
        "/v1/attempts",
        json={"item_id": item.id, "text": "hello world"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["item_id"] == item.id
    assert payload["percentage"] >= 0
    assert payload["wer"] >= 0


def test_create_attempt_endpoint_returns_404_for_missing_item(test_client):
    response = test_client.post(
        "/v1/attempts",
        json={"item_id": 999999, "text": "hello"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_list_attempts_endpoint_filters_by_item(
    test_client, db_manager, attempts_service
):
    item_a = _create_item(db_manager, text="alpha")
    item_b = _create_item(db_manager, text="beta")
    attempts_service.create_attempt(item_a.id, "alpha")
    attempts_service.create_attempt(item_b.id, "beta")

    response = test_client.get("/v1/attempts", params={"item_id": item_a.id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["attempts"]) == 1
    assert payload["attempts"][0]["item_id"] == item_a.id


def test_get_attempt_endpoint_returns_attempt(
    test_client, db_manager, attempts_service
):
    item = _create_item(db_manager, text="gamma delta")
    attempt = attempts_service.create_attempt(item.id, "gamma delta")

    response = test_client.get(f"/v1/attempts/{attempt.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == attempt.id
    assert payload["item_id"] == item.id
