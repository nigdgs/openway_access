"""
Минимальные MVP-тесты для POST /api/v1/access/verify
Проверка работы с DRF user-token + RBAC
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.access.models import AccessPermission, AccessPoint

User = get_user_model()


class VerifyMVPTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/access/verify"

    def test_allow_user_token(self):
        """ALLOW: валидный user token + существующий gate + есть разрешение"""
        # Создаём активного пользователя
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)

        # Создаём user token
        token = Token.objects.create(user=user)

        # Создаём gate
        gate = AccessPoint.objects.create(code="gate-01", name="Main Gate")

        # RBAC: даём разрешение пользователю
        AccessPermission.objects.create(access_point=gate, user=user, allow=True)

        # Запрос
        response = self.client.post(self.url, {
            "gate_id": "gate-01",
            "token": token.key
        }, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n✅ test_allow_user_token: {data}")

        self.assertEqual(data["decision"], "ALLOW")
        self.assertEqual(data["reason"], "OK")
        self.assertEqual(data["duration_ms"], 800)

    def test_token_invalid(self):
        """DENY: невалидный token"""
        # Создаём gate
        gate = AccessPoint.objects.create(code="gate-01", name="Main Gate")

        # Запрос с невалидным токеном
        response = self.client.post(self.url, {
            "gate_id": "gate-01",
            "token": "invalid_token_12345"
        }, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n❌ test_token_invalid: {data}")

        self.assertEqual(data["decision"], "DENY")
        self.assertEqual(data["reason"], "TOKEN_INVALID")
        self.assertNotIn("duration_ms", data)

    def test_unknown_gate(self):
        """DENY: неизвестный gate"""
        # Создаём валидного user + token
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        token = Token.objects.create(user=user)

        # НЕ создаём gate

        # Запрос к несуществующему gate
        response = self.client.post(self.url, {
            "gate_id": "gate-99-unknown",
            "token": token.key
        }, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n❌ test_unknown_gate: {data}")

        self.assertEqual(data["decision"], "DENY")
        self.assertEqual(data["reason"], "UNKNOWN_GATE")
        self.assertNotIn("duration_ms", data)

    def test_invalid_request(self):
        """DENY: невалидный request (пустой payload)"""
        # Запрос без обязательных полей
        response = self.client.post(self.url, {}, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n❌ test_invalid_request: {data}")

        self.assertEqual(data["decision"], "DENY")
        self.assertEqual(data["reason"], "INVALID_REQUEST")
        self.assertNotIn("duration_ms", data)

    def test_allow_via_group(self):
        """ALLOW: разрешение через группу пользователя"""
        # Создаём пользователя и группу
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        group = Group.objects.create(name="Engineers")
        user.groups.add(group)

        # Создаём user token
        token = Token.objects.create(user=user)

        # Создаём gate
        gate = AccessPoint.objects.create(code="gate-02", name="Engineering Gate")

        # RBAC: даём разрешение группе (не пользователю напрямую)
        AccessPermission.objects.create(access_point=gate, group=group, allow=True)

        # Запрос
        response = self.client.post(self.url, {
            "gate_id": "gate-02",
            "token": token.key
        }, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n✅ test_allow_via_group: {data}")

        self.assertEqual(data["decision"], "ALLOW")
        self.assertEqual(data["reason"], "OK")
        self.assertEqual(data["duration_ms"], 800)

    def test_no_permission(self):
        """DENY: нет разрешения ни для пользователя, ни для группы"""
        # Создаём пользователя
        user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
        token = Token.objects.create(user=user)

        # Создаём gate
        gate = AccessPoint.objects.create(code="gate-03", name="Restricted Gate")

        # НЕ даём никаких разрешений

        # Запрос
        response = self.client.post(self.url, {
            "gate_id": "gate-03",
            "token": token.key
        }, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n❌ test_no_permission: {data}")

        self.assertEqual(data["decision"], "DENY")
        self.assertEqual(data["reason"], "NO_PERMISSION")
        self.assertNotIn("duration_ms", data)

    def test_inactive_user(self):
        """DENY: неактивный пользователь"""
        # Создаём НЕАКТИВНОГО пользователя
        user = User.objects.create_user(username="testuser", password="pass123", is_active=False)
        token = Token.objects.create(user=user)

        # Создаём gate с разрешением
        gate = AccessPoint.objects.create(code="gate-04", name="Test Gate")
        AccessPermission.objects.create(access_point=gate, user=user, allow=True)

        # Запрос
        response = self.client.post(self.url, {
            "gate_id": "gate-04",
            "token": token.key
        }, format="json")

        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"\n❌ test_inactive_user: {data}")

        self.assertEqual(data["decision"], "DENY")
        self.assertEqual(data["reason"], "TOKEN_INVALID")
        self.assertNotIn("duration_ms", data)

