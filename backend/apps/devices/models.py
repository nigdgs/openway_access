from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    name = models.CharField(max_length=100, blank=True)
    android_device_id = models.CharField(max_length=128, blank=True, null=True)
    totp_secret = models.CharField(max_length=64, blank=True)  # base32 - kept for future use
    auth_token = models.CharField(max_length=64, unique=True)  # static token for auth
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)