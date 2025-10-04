"""
Тесты для проверки правильного разрешения URL через core.urls
"""
from django.test import TestCase
from django.urls import resolve, reverse

from apps.api.v1.views import AccessVerifyView


class URLResolveTests(TestCase):
    """Проверка, что URL корректно разрешается через core.urls → apps.api.urls → apps.api.v1.urls"""

    def test_verify_url_resolves(self):
        """Проверка, что /api/v1/access/verify разрешается в AccessVerifyView"""
        match = resolve("/api/v1/access/verify")
        self.assertIsNotNone(match)
        self.assertEqual(match.func.view_class, AccessVerifyView)
        self.assertEqual(match.url_name, "access-verify")

    def test_verify_url_reverse(self):
        """Проверка, что reverse('access-verify') возвращает правильный URL"""
        url = reverse("access-verify")
        self.assertEqual(url, "/api/v1/access/verify")

    def test_auth_token_url_resolves(self):
        """Проверка, что /api/v1/auth/token разрешается корректно"""
        match = resolve("/api/v1/auth/token")
        self.assertIsNotNone(match)
        self.assertEqual(match.url_name, "auth-token")

    def test_devices_register_url_resolves(self):
        """Проверка, что /api/v1/devices/register разрешается корректно"""
        match = resolve("/api/v1/devices/register")
        self.assertIsNotNone(match)
        self.assertEqual(match.url_name, "devices-register")

