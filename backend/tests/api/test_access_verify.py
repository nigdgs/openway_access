from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.devices.models import Device
from apps.access.models import AccessPoint, AccessPermission, AccessEvent

User = get_user_model()

class StaticTokenVerifyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("access-verify")
        self.ap = AccessPoint.objects.create(code="gate-01", name="Gate 01")
        self.grp = Group.objects.create(name="USER")

        self.user = User.objects.create_user(username="u1", password="x")
        self.user.groups.add(self.grp)
        AccessPermission.objects.create(access_point=self.ap, group=self.grp, allow=True)

        self.device = Device.objects.create(user=self.user, auth_token="tok123456789", is_active=True)

    def test_allow(self):
        resp = self.client.post(self.url, {"gate_id":"gate-01","token":"tok123456789"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("decision"), "ALLOW")
        self.assertEqual(resp.data.get("reason"), "OK")
        self.assertIn("duration_ms", resp.data)

    def test_token_invalid(self):
        resp = self.client.post(self.url, {"gate_id":"gate-01","token":"nope"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("decision"), "DENY")
        self.assertEqual(resp.data.get("reason"), "TOKEN_INVALID")

    def test_inactive_device(self):
        self.device.is_active = False
        self.device.save(update_fields=["is_active"])
        resp = self.client.post(self.url, {"gate_id":"gate-01","token":"tok123456789"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("decision"), "DENY")
        self.assertEqual(resp.data.get("reason"), "DEVICE_INACTIVE")

    def test_no_permission(self):
        # remove group permission or user's group
        self.user.groups.clear()
        resp = self.client.post(self.url, {"gate_id":"gate-01","token":"tok123456789"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("decision"), "DENY")
        self.assertEqual(resp.data.get("reason"), "NO_PERMISSION")

    def test_unknown_gate(self):
        resp = self.client.post(self.url, {"gate_id":"unknown","token":"tok123456789"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("decision"), "DENY")
        self.assertEqual(resp.data.get("reason"), "UNKNOWN_GATE")

    def test_invalid_request(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("gate_id", resp.data)
        self.assertIn("token", resp.data)

    def test_raw_data_security(self):
        """Проверяем, что в AccessEvent.raw не сохраняется полный токен"""
        # Выполняем запрос с валидным токеном
        resp = self.client.post(self.url, {"gate_id":"gate-01","token":"tok123456789"}, format="json")
        self.assertEqual(resp.status_code, 200)
        
        # Проверяем, что событие создалось
        event = AccessEvent.objects.filter(decision="ALLOW").first()
        self.assertIsNotNone(event)
        self.assertIsNotNone(event.raw)
        
        # Проверяем, что полный токен НЕ сохранен
        self.assertNotIn("token", event.raw)
        
        # Проверяем, что token_preview сохранен
        self.assertIn("token_preview", event.raw)
        self.assertEqual(event.raw["token_preview"], "tok1…6789")
        
        # Проверяем другие обязательные поля
        self.assertIn("transport", event.raw)
        self.assertEqual(event.raw["transport"], "wifi")
        self.assertIn("gate_id", event.raw)
        self.assertEqual(event.raw["gate_id"], "gate-01")
        self.assertIn("processing_ms", event.raw)
        self.assertIsInstance(event.raw["processing_ms"], int)

    def test_raw_data_security_deny(self):
        """Проверяем безопасность raw данных для DENY ответов"""
        # Выполняем запрос с невалидным токеном
        resp = self.client.post(self.url, {"gate_id":"gate-01","token":"invalid_token_12345"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("decision"), "DENY")
        
        # Проверяем, что событие создалось
        event = AccessEvent.objects.filter(decision="DENY", reason="TOKEN_INVALID").first()
        self.assertIsNotNone(event)
        self.assertIsNotNone(event.raw)
        
        # Проверяем, что полный токен НЕ сохранен
        self.assertNotIn("token", event.raw)
        
        # Проверяем, что token_preview сохранен
        self.assertIn("token_preview", event.raw)
        self.assertEqual(event.raw["token_preview"], "inva…2345")