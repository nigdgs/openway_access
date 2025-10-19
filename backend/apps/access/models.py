from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class AccessPoint(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=128, blank=True)

    class Meta:
        verbose_name = _("Точка доступа")
        verbose_name_plural = _("Точки доступа")

    def __str__(self):
        return self.code

class AccessPermission(models.Model):
    access_point = models.ForeignKey(AccessPoint, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    allow = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Право доступа")
        verbose_name_plural = _("Права доступа")
        unique_together = (("access_point", "user", "group"),)
        constraints = [
            models.CheckConstraint(
                name="ap_perm_user_or_group_not_null",
                check=Q(user__isnull=False) | Q(group__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=["access_point", "user"]),
            models.Index(fields=["access_point", "group"]),
        ]

class AccessEvent(models.Model):
    access_point = models.ForeignKey(AccessPoint, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    device_id = models.IntegerField(null=True, blank=True)
    decision = models.CharField(max_length=10)  # "ALLOW"/"DENY"
    reason = models.CharField(max_length=64, blank=True)
    raw = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Событие доступа")
        verbose_name_plural = _("События доступа")
        ordering = ("-created_at",)
