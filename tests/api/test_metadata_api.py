"""API tests for the /metadata endpoint."""


def test_metadata_endpoint_returns_expected_sections(test_client):
    response = test_client.get("/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"]["name"]
    assert "build" in payload
    assert "runtime" in payload
    assert "providers" in payload


def test_metadata_endpoint_allows_field_filtering(test_client):
    response = test_client.get("/metadata?detail=runtime&fields=runtime")

    assert response.status_code == 200
    payload = response.json()
    assert "runtime" in payload
    assert "build" not in payload
