"""Tests for DRF permission defaults."""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


@pytest.mark.django_db
class TestPermissionDefaults:
    """Test that default permissions are IsAuthenticated."""

    def test_unauthenticated_access_to_private_api_returns_401(self):
        """Test unauthenticated access to /api/v1/devices/me returns 401."""
        client = Client()
        response = client.get("/api/v1/devices/me")
        assert response.status_code == 401

    def test_public_endpoints_allow_unauthenticated_access(self):
        """Test public endpoints are accessible without authentication."""
        client = Client()
        
        # Health endpoints should be accessible
        response = client.get("/health")
        assert response.status_code == 200
        
        response = client.get("/healthz")
        assert response.status_code == 200
        
        response = client.get("/ready")
        assert response.status_code == 200
        
        response = client.get("/readyz")
        assert response.status_code == 200

    def test_authenticated_access_to_private_api_works(self):
        """Test authenticated access to private API works."""
        # Create user and token
        user = User.objects.create_user(username="testuser", password="testpass")
        token = Token.objects.create(user=user)
        
        client = Client()
        response = client.get(
            "/api/v1/devices/me",
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )
        # Should return 200 (even if no devices exist)
        assert response.status_code == 200

