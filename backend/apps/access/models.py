from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings

class AccessPoint(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.code

class AccessPermission(models.Model):
    access_point = models.ForeignKey(AccessPoint, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    allow = models.BooleanField(default=True)

    class Meta:
        unique_together = (("access_point", "user", "group"),)

class AccessEvent(models.Model):
    access_point = models.ForeignKey(AccessPoint, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    device_id = models.IntegerField(null=True, blank=True)
    decision = models.CharField(max_length=10)  # "ALLOW"/"DENY"
    reason = models.CharField(max_length=64, blank=True)
    # Пример содержимого raw:
    # {
    #   "transport": "wifi",
    #   "remote_ip": "192.168.1.10",
    #   "gate_id": "gate-01",
    #   "token_preview": "abcd…wxyz",
    #   "processing_ms": 12,
    #   "request_id": "uuid-or-header",
    # }
    # Полный token никогда не сохраняется.
    raw = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)