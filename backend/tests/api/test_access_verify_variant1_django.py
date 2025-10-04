"""
Тесты для /api/v1/access/verify - Вариант 1 (user_session_token + RBAC)
Django TestCase версия (без pytest)

Проверяем:
- Валидацию DRF user token (не Device.auth_token)
- RBAC через AccessPermission (user или group)
- Все сценарии ALLOW/DENY
- Rate limiting
"""
from unittest import skip

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.access.models import AccessPermission, AccessPoint

User = get_user_model()
VERIFY_URL = "/api/v1/access/verify"


def make_user_with_token(username="u1", password="p1"):
    """Создаёт пользователя с DRF токеном"""
    u = User.objects.create_user(username=username, password=password, is_active=True)
    t, _ = Token.objects.get_or_create(user=u)
    return u, t.key


class TestAccessVerifyVariant1(TestCase):
    """Тесты Варианта 1: единый user_session_token + RBAC"""

    def setUp(self):
        self.client = APIClient()
        # Очищаем кеш throttle перед каждым тестом
        cache.clear()

    def tearDown(self):
        # Очищаем кеш throttle после каждого теста
        cache.clear()

    def test_allow_by_user_permission(self):
        """✅ ALLOW: разрешение напрямую для пользователя"""
        gate = AccessPoint.objects.create(code="gate-01", name="Main Gate")
        u, token = make_user_with_token()
        AccessPermission.objects.create(access_point=gate, user=u, allow=True)

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-01", "token": token}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "ALLOW")
        self.assertEqual(body["reason"], "OK")
        self.assertIn("duration_ms", body)
        self.assertEqual(body["duration_ms"], 800)

    def test_allow_by_group_permission(self):
        """✅ ALLOW: разрешение через группу пользователя"""
        gate = AccessPoint.objects.create(code="gate-02", name="Side Gate")
        u, token = make_user_with_token("u2")
        g = Group.objects.create(name="Engineers")
        u.groups.add(g)
        AccessPermission.objects.create(access_point=gate, group=g, allow=True)

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-02", "token": token}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "ALLOW")
        self.assertEqual(body["reason"], "OK")
        self.assertIn("duration_ms", body)

    def test_deny_no_permission(self):
        """❌ DENY: нет разрешения ни для user, ни для группы"""
        gate = AccessPoint.objects.create(code="gate-03", name="NoPerm Gate")
        u, token = make_user_with_token("u3")
        # НЕ создаём AccessPermission

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-03", "token": token}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "DENY")
        self.assertEqual(body["reason"], "NO_PERMISSION")
        self.assertNotIn("duration_ms", body)

    def test_deny_unknown_gate(self):
        """❌ DENY: gate_id не существует"""
        u, token = make_user_with_token("u4")

        resp = self.client.post(VERIFY_URL, {"gate_id": "unknown-gate", "token": token}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "DENY")
        self.assertEqual(body["reason"], "UNKNOWN_GATE")

    def test_deny_invalid_token(self):
        """❌ DENY: токен невалидный (не существует в БД)"""
        gate = AccessPoint.objects.create(code="gate-05", name="Main Gate")

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-05", "token": "invalid_token_12345"}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "DENY")
        self.assertEqual(body["reason"], "TOKEN_INVALID")

    def test_deny_inactive_user(self):
        """❌ DENY: пользователь неактивен"""
        gate = AccessPoint.objects.create(code="gate-06", name="Test Gate")
        u = User.objects.create_user(username="inactive_user", password="p", is_active=False)
        t, _ = Token.objects.get_or_create(user=u)
        AccessPermission.objects.create(access_point=gate, user=u, allow=True)

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-06", "token": t.key}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "DENY")
        self.assertEqual(body["reason"], "TOKEN_INVALID")

    def test_deny_invalid_request_empty(self):
        """❌ DENY: пустой запрос"""
        resp = self.client.post(VERIFY_URL, {}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "DENY")
        self.assertEqual(body["reason"], "INVALID_REQUEST")

    def test_allow_multiple_groups(self):
        """✅ ALLOW: пользователь в нескольких группах, одна из них имеет доступ"""
        gate = AccessPoint.objects.create(code="gate-07", name="Multi Group Gate")
        u, token = make_user_with_token("u7")

        g1 = Group.objects.create(name="Group1")
        g2 = Group.objects.create(name="Group2")
        u.groups.add(g1, g2)

        # Разрешение только для g2
        AccessPermission.objects.create(access_point=gate, group=g2, allow=True)

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-07", "token": token}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "ALLOW")
        self.assertEqual(body["reason"], "OK")

    def test_user_permission_overrides_no_group(self):
        """✅ ALLOW: у пользователя есть прямое разрешение, даже если группы без прав"""
        gate = AccessPoint.objects.create(code="gate-08", name="User Override Gate")
        u, token = make_user_with_token("u8")

        g = Group.objects.create(name="NoAccessGroup")
        u.groups.add(g)

        # Прямое разрешение пользователю (группе не даём)
        AccessPermission.objects.create(access_point=gate, user=u, allow=True)

        resp = self.client.post(VERIFY_URL, {"gate_id": "gate-08", "token": token}, format="json")
        body = resp.json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(body["decision"], "ALLOW")
        self.assertEqual(body["reason"], "OK")


class TestAccessVerifyRateLimit(TestCase):
    """Тесты rate limiting для /verify"""

    def setUp(self):
        self.client = APIClient()
        # Очищаем кеш throttle перед каждым тестом
        cache.clear()

    def tearDown(self):
        # Очищаем кеш throttle после каждого теста
        cache.clear()

    @skip("Throttling override_settings не работает должным образом в unit-тестах. Проверяется smoke-тестами.")
    @override_settings(REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.ScopedRateThrottle'],
        'DEFAULT_THROTTLE_RATES': {'access_verify': '10/minute'}
    })
    def test_rate_limit_triggers_deny(self):
        """✅ Rate limit: при превышении лимита возвращается DENY/RATE_LIMIT"""
        gate = AccessPoint.objects.create(code="gate-rl", name="Rate Limit Gate")
        u, token = make_user_with_token("rl_user")
        AccessPermission.objects.create(access_point=gate, user=u, allow=True)

        rate_limited_count = 0
        num_requests = 40

        # Отправляем много запросов подряд
        for i in range(num_requests):
            resp = self.client.post(
                VERIFY_URL,
                {"gate_id": "gate-rl", "token": token},
                format="json"
            )
            body = resp.json()

            if body.get("reason") == "RATE_LIMIT":
                rate_limited_count += 1

        # Хотя бы один запрос должен получить RATE_LIMIT
        self.assertGreater(rate_limited_count, 0,
                          f"Expected at least 1 RATE_LIMIT, got {rate_limited_count}")
        print(f"\n✅ Rate limit triggered {rate_limited_count} times out of {num_requests} requests")

