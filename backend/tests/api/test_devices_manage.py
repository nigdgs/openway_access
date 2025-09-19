from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from apps.devices.models import Device

User = get_user_model()

class DeviceManageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="bob", password="x")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.url_me = "/api/v1/devices/me"
        self.url_reg = "/api/v1/devices/register"
        self.url_revoke = "/api/v1/devices/revoke"

    def test_list_empty(self):
        r = self.client.get(self.url_me)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [])

    def test_register_updates_android_id_without_rotate(self):
        r1 = self.client.post(self.url_reg, {}, format="json")
        self.assertEqual(r1.status_code, 200)
        dev_id = r1.data["device_id"]
        # update android id without rotate (explicitly set rotate=False)
        r2 = self.client.post(self.url_reg, {"android_device_id":"android-123", "rotate": False}, format="json")
        self.assertEqual(r2.status_code, 200)
        d = Device.objects.get(pk=dev_id)
        self.assertEqual(d.android_device_id, "android-123")
        # token remains the same
        self.assertEqual(r1.data["token"], r2.data["token"])

    def test_list_and_revoke(self):
        r1 = self.client.post(self.url_reg, {"android_device_id":"xyz"}, format="json")
        dev_id = r1.data["device_id"]
        r_list = self.client.get(self.url_me)
        self.assertEqual(r_list.status_code, 200)
        self.assertTrue(any(item["id"] == dev_id for item in r_list.data))
        r_rev = self.client.post(self.url_revoke, {"device_id": dev_id}, format="json")
        self.assertEqual(r_rev.status_code, 200)
        self.assertEqual(r_rev.data["device_id"], dev_id)
        self.assertEqual(r_rev.data["is_active"], False)

