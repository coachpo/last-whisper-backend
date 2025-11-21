"""Integration tests for items API endpoints."""

from app.models.enums import ItemTTSStatus


def test_get_item_tts_status_returns_payload(test_client, items_service):
    item = items_service.create_item(locale="en-US", text="Sample dictation text")

    response = test_client.get(f"/v1/items/{item['id']}/tts-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_id"] == item["id"]
    assert payload["tts_status"] == ItemTTSStatus.PENDING.value
    assert payload["text"].startswith("Sample")


def test_get_item_tts_status_returns_404_for_missing_item(test_client):
    response = test_client.get("/v1/items/999999/tts-status")

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"
