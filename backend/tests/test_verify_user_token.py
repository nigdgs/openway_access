import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.access.models import AccessPermission, AccessPoint

User = get_user_model()


@pytest.mark.django_db
class TestAccessVerifyUserToken:
    """Тесты для POST /api/v1/access/verify с DRF user-token + RBAC"""

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/v1/access/verify"

    def test_allow_user_token(self):
        """ALLOW: валидный user token + существующий gate + есть разрешение"""
        # Setup
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        token = Token.objects.create(user=user)
        gate = AccessPoint.objects.create(code="gate-01", name="Test Gate")

        # RBAC: даём разрешение пользователю
        AccessPermission.objects.create(access_point=gate, user=user, allow=True)

        # Request
        response = self.client.post(self.url, {
            "gate_id": "gate-01",
            "token": token.key
        }, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "ALLOW"
        assert data["reason"] == "OK"
        assert data["duration_ms"] == 800

        print(f"\ntest_allow_user_token response: {data}")

    def test_token_invalid(self):
        """DENY: невалидный token"""
        # Setup
        gate = AccessPoint.objects.create(code="gate-01", name="Test Gate")

        # Request
        response = self.client.post(self.url, {
            "gate_id": "gate-01",
            "token": "invalid_token_12345"
        }, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "DENY"
        assert data["reason"] == "TOKEN_INVALID"
        assert data.get("duration_ms") == 0 or "duration_ms" not in data

        print(f"\ntest_token_invalid response: {data}")

    def test_unknown_gate(self):
        """DENY: несуществующий gate"""
        # Setup
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        token = Token.objects.create(user=user)

        # Request (gate не создан)
        response = self.client.post(self.url, {
            "gate_id": "gate-99",
            "token": token.key
        }, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "DENY"
        assert data["reason"] == "UNKNOWN_GATE"
        assert data.get("duration_ms") == 0 or "duration_ms" not in data

        print(f"\ntest_unknown_gate response: {data}")

    def test_invalid_request(self):
        """DENY: пустой запрос"""
        # Request
        response = self.client.post(self.url, {}, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "DENY"
        assert data["reason"] == "INVALID_REQUEST"
        assert data.get("duration_ms") == 0 or "duration_ms" not in data

        print(f"\ntest_invalid_request response: {data}")

    def test_allow_via_group(self):
        """ALLOW: разрешение через группу пользователя"""
        # Setup
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        group = Group.objects.create(name="Engineers")
        user.groups.add(group)
        token = Token.objects.create(user=user)
        gate = AccessPoint.objects.create(code="gate-02", name="Engineering Gate")

        # RBAC: даём разрешение группе (не пользователю напрямую)
        AccessPermission.objects.create(access_point=gate, group=group, allow=True)

        # Request
        response = self.client.post(self.url, {
            "gate_id": "gate-02",
            "token": token.key
        }, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "ALLOW"
        assert data["reason"] == "OK"
        assert data["duration_ms"] == 800

        print(f"\ntest_allow_via_group response: {data}")

    def test_no_permission(self):
        """DENY: нет разрешения ни для пользователя, ни для группы"""
        # Setup
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        token = Token.objects.create(user=user)
        gate = AccessPoint.objects.create(code="gate-03", name="Restricted Gate")

        # НЕ даём никаких разрешений

        # Request
        response = self.client.post(self.url, {
            "gate_id": "gate-03",
            "token": token.key
        }, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "DENY"
        assert data["reason"] == "NO_PERMISSION"
        assert "duration_ms" not in data

        print(f"\ntest_no_permission response: {data}")

    def test_inactive_user(self):
        """DENY: неактивный пользователь"""
        # Setup
        user = User.objects.create_user(username="testuser", password="pass123", is_active=False)
        token = Token.objects.create(user=user)
        gate = AccessPoint.objects.create(code="gate-04", name="Test Gate")
        AccessPermission.objects.create(access_point=gate, user=user, allow=True)

        # Request
        response = self.client.post(self.url, {
            "gate_id": "gate-04",
            "token": token.key
        }, format="json")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "DENY"
        assert data["reason"] == "TOKEN_INVALID"
        assert "duration_ms" not in data

        print(f"\ntest_inactive_user response: {data}")

