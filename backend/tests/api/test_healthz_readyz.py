"""Tests for /healthz and /readyz endpoints."""
import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealthzReadyz:
    """Test Kubernetes-style health endpoints."""

    def test_healthz_returns_200(self):
        """Test /healthz endpoint returns 200 OK."""
        client = Client()
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readyz_returns_200_when_db_available(self):
        """Test /readyz endpoint returns 200 when database is available."""
        client = Client()
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

