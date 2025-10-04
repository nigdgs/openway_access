from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.devices.models import Device

User = get_user_model()

class DeviceRegisterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", password="x")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.url_auth = "/api/v1/auth/token"
        self.url_reg = "/api/v1/devices/register"

    def test_obtain_auth_token(self):
        resp = self.client.post(self.url_auth, {"username":"alice","password":"x"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)

    def test_register_creates_device_and_returns_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        resp = self.client.post(self.url_reg, {"android_device_id":"android-abc"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("device_id", resp.data)
        self.assertIn("token", resp.data)
        self.assertIn("qr_payload", resp.data)
        self.assertEqual(resp.data.get("android_device_id"), "android-abc")
        d = Device.objects.get(pk=resp.data["device_id"])
        self.assertEqual(d.user_id, self.user.id)
        self.assertEqual(d.android_device_id, "android-abc")
        self.assertTrue(d.is_active)
        self.assertTrue(d.auth_token)

    def test_register_rotate_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        # first create
        r1 = self.client.post(self.url_reg, {"android_device_id":"android-abc"}, format="json")
        t1 = r1.data["token"]
        # rotate
        r2 = self.client.post(self.url_reg, {"android_device_id":"android-abc","rotate":True}, format="json")
        t2 = r2.data["token"]
        self.assertNotEqual(t1, t2)

    def test_register_rotate_false_keeps_token_and_updates_android_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        first = self.client.post(self.url_reg, {"android_device_id":"android-old"}, format="json")
        token_initial = first.data["token"]

        second = self.client.post(
            self.url_reg,
            {"android_device_id": "android-new", "rotate": False},
            format="json",
        )

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["token"], token_initial)
        self.assertEqual(second.data.get("android_device_id"), "android-new")

        device = Device.objects.get(pk=second.data["device_id"])
        self.assertEqual(device.android_device_id, "android-new")
        self.assertEqual(device.auth_token, token_initial)
