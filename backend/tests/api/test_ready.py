import pytest


@pytest.mark.django_db
def test_ready_ok(client):
    """Test readiness probe returns 200 when DB is available."""
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"

