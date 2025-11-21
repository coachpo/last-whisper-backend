def create_item(test_client, locale="fi", text="hello world"):
    resp = test_client.post(
        "/v1/items",
        json={"locale": locale, "text": text, "difficulty": 1},
    )
    assert resp.status_code == 202
    return resp.json()["id"]


def test_translation_rejects_same_source_and_target(test_client):
    item_id = create_item(test_client, locale="fi")

    resp = test_client.post(
        f"/v1/items/{item_id}/translations",
        json={"target_lang": "fi"},
    )

    assert resp.status_code == 400
    body = resp.json()
    assert "Invalid translation request" in body.get("detail", "")


def test_translation_success_with_stub_provider(test_client, translation_manager):
    item_id = create_item(test_client, locale="fi")

    resp = test_client.post(
        f"/v1/items/{item_id}/translations",
        json={"target_lang": "en"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == item_id
    assert data["target_lang"] == "en"
    assert data["cached"] is False


def test_audio_refresh_enqueues_task(test_client, task_manager):
    item_id = create_item(test_client, locale="fi")

    resp = test_client.post(f"/v1/items/{item_id}/audio/refresh")
    assert resp.status_code == 202
    data = resp.json()
    assert data["item_id"] == item_id
    assert data["task_id"]
    # Ensure task manager captured the submission
    assert len(task_manager.submissions) >= 1
