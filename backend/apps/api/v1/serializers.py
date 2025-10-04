from rest_framework import serializers

from .constants import DECISIONS, REASONS


class VerifyRequestSerializer(serializers.Serializer):
    gate_id = serializers.CharField()
    token = serializers.CharField(min_length=8, max_length=128)

class VerifyResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=list(DECISIONS))
    duration_ms = serializers.IntegerField(required=False, min_value=0)
    reason = serializers.ChoiceField(choices=list(REASONS))

class DeviceRegisterRequestSerializer(serializers.Serializer):
    # Ротация по умолчанию включена — вариант А (обновляем токен при входе/возврате приложения)
    rotate = serializers.BooleanField(required=False, default=True)
    android_device_id = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=128)

class DeviceRegisterResponseSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    token = serializers.CharField()
    android_device_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    qr_payload = serializers.CharField()

class DeviceMeItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    android_device_id = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()
    token_preview = serializers.CharField()

class DeviceRevokeRequestSerializer(serializers.Serializer):
    device_id = serializers.IntegerField(required=False)
    android_device_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get("device_id") and not data.get("android_device_id"):
            raise serializers.ValidationError("Provide device_id or android_device_id")
        return data

class DeviceRevokeResponseSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    is_active = serializers.BooleanField()
