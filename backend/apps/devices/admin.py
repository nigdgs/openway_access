from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "is_active", "created_at")
    search_fields = ("user__username", "android_device_id")
    readonly_fields = ("auth_token",)
