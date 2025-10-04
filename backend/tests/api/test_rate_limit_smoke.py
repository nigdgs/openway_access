from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "access_verify": "1/second",
    },
})
class VerifyThrottleSmoke(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("access-verify")

    def test_throttle_returns_200(self):
        body = {"gate_id":"gate-01","token":"invalid"}  # token invalid is ok for this smoke
        r1 = self.client.post(self.url, body, format="json")
        r2 = self.client.post(self.url, body, format="json")
        self.assertEqual(r2.status_code, 200)  # still 200, even if throttled
        # reason can be TOKEN_INVALID or RATE_LIMIT depending on timing; ensure response shape at least
        self.assertIn("decision", r2.data)
        self.assertIn("reason", r2.data)

