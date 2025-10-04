from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.access.models import AccessPermission, AccessPoint
from apps.devices.models import Device

User = get_user_model()


class AndroidIntegrationTestCase(TestCase):
    """Test cases for Android integration endpoints and behavior."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test user and token
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.token = Token.objects.create(user=self.user)

        # Create access point for verify tests
        self.access_point = AccessPoint.objects.create(
            code='test_gate',
            name='Test Gate',
            location='Test location'
        )

        # Create permission for the user
        AccessPermission.objects.create(
            access_point=self.access_point,
            user=self.user,
            allow=True
        )

    def test_health_ok(self):
        """Test /health endpoint returns 200 with correct JSON."""
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_register_returns_android_id(self):
        """Test POST /api/v1/devices/register returns android_device_id in response."""
        self.client.force_authenticate(user=self.user, token=self.token)

        android_id = "test_android_device_123"
        data = {
            "android_device_id": android_id,
            "rotate": True
        }

        response = self.client.post('/api/v1/devices/register', data, format='json')

        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        # Check required fields
        self.assertIn('device_id', response_data)
        self.assertIn('token', response_data)
        self.assertIn('qr_payload', response_data)
        self.assertIn('android_device_id', response_data)

        # Check android_device_id is returned
        self.assertEqual(response_data['android_device_id'], android_id)

        # Check token length (64 hex characters)
        self.assertEqual(len(response_data['token']), 64)

        # Check qr_payload equals token
        self.assertEqual(response_data['qr_payload'], response_data['token'])

    def test_register_rotate_false_keeps_token(self):
        """Test that rotate=False keeps the same token when updating android_device_id."""
        self.client.force_authenticate(user=self.user, token=self.token)

        # First call: register with rotate=True (default)
        data1 = {
            "android_device_id": "android_device_1",
            "rotate": True
        }
        response1 = self.client.post('/api/v1/devices/register', data1, format='json')
        self.assertEqual(response1.status_code, 200)
        token1 = response1.json()['token']

        # Second call: update android_device_id with rotate=False
        data2 = {
            "android_device_id": "android_device_2",
            "rotate": False
        }
        response2 = self.client.post('/api/v1/devices/register', data2, format='json')
        self.assertEqual(response2.status_code, 200)
        token2 = response2.json()['token']

        # Token should remain the same
        self.assertEqual(token1, token2)

        # android_device_id should be updated
        self.assertEqual(response2.json()['android_device_id'], "android_device_2")

    def test_register_rotate_default_true(self):
        """Test that rotate defaults to True when not specified."""
        self.client.force_authenticate(user=self.user, token=self.token)

        # First call: get initial token
        data1 = {"android_device_id": "test_device"}
        response1 = self.client.post('/api/v1/devices/register', data1, format='json')
        self.assertEqual(response1.status_code, 200)
        token1 = response1.json()['token']

        # Second call: no rotate specified (should default to True)
        data2 = {"android_device_id": "test_device"}
        response2 = self.client.post('/api/v1/devices/register', data2, format='json')
        self.assertEqual(response2.status_code, 200)
        token2 = response2.json()['token']

        # Token should be different (rotated)
        self.assertNotEqual(token1, token2)

    def test_verify_200_contract(self):
        """Test POST /api/v1/access/verify always returns 200 with required fields."""
        # Create a device with token
        device = Device.objects.create(
            user=self.user,
            auth_token='test_token_123',
            is_active=True
        )

        # Test successful verification
        data = {
            "gate_id": "test_gate",
            "token": "test_token_123"
        }

        response = self.client.post('/api/v1/access/verify', data, format='json')

        # Always returns 200
        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        # Required fields
        self.assertIn('decision', response_data)
        self.assertIn('reason', response_data)

        # Optional field
        if 'duration_ms' in response_data:
            self.assertIsInstance(response_data['duration_ms'], int)
            self.assertGreaterEqual(response_data['duration_ms'], 0)

    def test_verify_deny_unknown_gate(self):
        """Test verify returns 200 DENY for unknown gate."""
        data = {
            "gate_id": "unknown_gate",
            "token": "test_token_123"
        }

        response = self.client.post('/api/v1/access/verify', data, format='json')

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['decision'], 'DENY')

    def test_verify_deny_invalid_token(self):
        """Test verify returns 200 DENY for invalid token."""
        data = {
            "gate_id": "test_gate",
            "token": "invalid_token"
        }

        response = self.client.post('/api/v1/access/verify', data, format='json')

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['decision'], 'DENY')

    def test_register_creates_device_if_none(self):
        """Test that register creates a new device if none exists."""
        self.client.force_authenticate(user=self.user, token=self.token)

        # Ensure no devices exist
        Device.objects.filter(user=self.user).delete()

        data = {"android_device_id": "new_device"}
        response = self.client.post('/api/v1/devices/register', data, format='json')

        self.assertEqual(response.status_code, 200)

        # Check device was created
        device = Device.objects.filter(user=self.user).first()
        self.assertIsNotNone(device)
        self.assertEqual(device.android_device_id, "new_device")
        self.assertTrue(device.is_active)

    def test_register_updates_existing_device(self):
        """Test that register updates existing device instead of creating new one."""
        self.client.force_authenticate(user=self.user, token=self.token)

        # Create existing device
        existing_device = Device.objects.create(
            user=self.user,
            auth_token='existing_token',
            is_active=True,
            android_device_id='old_android_id'
        )

        # Register with new android_device_id
        data = {
            "android_device_id": "new_android_id",
            "rotate": False
        }
        response = self.client.post('/api/v1/devices/register', data, format='json')

        self.assertEqual(response.status_code, 200)

        # Check device was updated, not created
        devices = Device.objects.filter(user=self.user)
        self.assertEqual(devices.count(), 1)

        device = devices.first()
        self.assertEqual(device.id, existing_device.id)
        self.assertEqual(device.android_device_id, "new_android_id")
        self.assertEqual(device.auth_token, "existing_token")  # Not rotated
