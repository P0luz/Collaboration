"""Product tier catalog tests for v5.2 commercial packaging."""

from fastapi.testclient import TestClient

from backend.collaboration.app import app


def test_plans_endpoint_returns_commercial_catalog_metadata():
    client = TestClient(app)

    response = client.get("/api/collaboration/plans")

    assert response.status_code == 200
    payload = response.json()
    assert payload["billing_implemented"] is False
    assert payload["relay_transmits_source_code"] is False
    assert [item["plan"] for item in payload["plans"]] == [
        "free",
        "team",
        "pro",
        "enterprise",
    ]

    free = payload["plans"][0]
    assert free["label"] == "Free"
    assert free["max_participants"] == 2
    assert free["relay_mode"] == "local"
    assert "local or self-hosted relay" in free["included"]

    team = payload["plans"][1]
    assert team["label"] == "Team"
    assert team["max_participants"] == 10
    assert team["relay_mode"] == "saas"
    assert "shared dashboard" in team["included"]

    enterprise = payload["plans"][3]
    assert enterprise["label"] == "Enterprise"
    assert enterprise["relay_mode"] == "private"
    assert "private relay" in enterprise["included"]
    assert "custom hook policy" in enterprise["reserved"]
