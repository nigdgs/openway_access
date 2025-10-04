import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.access.models import AccessEvent, AccessPermission, AccessPoint
from apps.devices.models import Device

from .constants import (
    REASON_INVALID_REQUEST,
    REASON_NO_PERMISSION,
    REASON_OK,
    REASON_RATE_LIMIT,
    REASON_TOKEN_INVALID,
    REASON_UNKNOWN_GATE,
)
from .serializers import (
    DeviceMeItemSerializer,
    DeviceRegisterRequestSerializer,
    DeviceRegisterResponseSerializer,
    DeviceRevokeRequestSerializer,
    DeviceRevokeResponseSerializer,
    VerifyRequestSerializer,
    VerifyResponseSerializer,
)

User = get_user_model()

def _respond(decision, reason, duration_ms=None):
    payload = {"decision": decision, "reason": reason}
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    ser = VerifyResponseSerializer(data=payload)
    ser.is_valid(raise_exception=True)
    return Response(ser.validated_data, status=status.HTTP_200_OK)

class AccessVerifyView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "access_verify"

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Throttled:
            # Log and return 200 DENY/RATE_LIMIT
            AccessEvent.objects.create(
                access_point=None, user=None, device_id=None,
                decision="DENY", reason=REASON_RATE_LIMIT, raw=request.data
            )
            return _respond("DENY", REASON_RATE_LIMIT)

    @extend_schema(
        operation_id="access-verify",
        tags=["Access"],
        request=VerifyRequestSerializer,
        responses={200: OpenApiResponse(response=VerifyResponseSerializer, description="ALLOW/DENY with reason")},
    )
    @transaction.atomic
    def post(self, request):
        # Normalize malformed payloads to 200/DENY + logging
        try:
            req = VerifyRequestSerializer(data=request.data)
            req.is_valid(raise_exception=True)
        except ValidationError:
            AccessEvent.objects.create(
                access_point=None, user=None, device_id=None,
                decision="DENY", reason=REASON_INVALID_REQUEST, raw=request.data
            )
            return _respond("DENY", REASON_INVALID_REQUEST)

        data = req.validated_data

        # Gate
        try:
            ap = AccessPoint.objects.get(code=data["gate_id"])
        except AccessPoint.DoesNotExist:
            AccessEvent.objects.create(access_point=None, user=None, device_id=None,
                                       decision="DENY", reason=REASON_UNKNOWN_GATE, raw=data)
            return _respond("DENY", REASON_UNKNOWN_GATE)

        # Token → User
        token = data["token"].strip()
        token_obj = Token.objects.select_related("user").filter(key=token).first()
        if not token_obj:
            AccessEvent.objects.create(access_point=ap, user=None, device_id=None,
                                       decision="DENY", reason=REASON_TOKEN_INVALID, raw=data)
            return _respond("DENY", REASON_TOKEN_INVALID)

        user = token_obj.user
        if not user.is_active:
            AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
                                       decision="DENY", reason=REASON_TOKEN_INVALID, raw=data)
            return _respond("DENY", REASON_TOKEN_INVALID)

        # RBAC: check if user or any of their groups has permission
        has_perm = AccessPermission.objects.filter(
            Q(access_point=ap, user=user, allow=True) |
            Q(access_point=ap, group__in=user.groups.all(), allow=True)
        ).exists()
        if not has_perm:
            AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
                                       decision="DENY", reason=REASON_NO_PERMISSION, raw=data)
            return _respond("DENY", REASON_NO_PERMISSION)

        # OK - Access granted
        AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
                                   decision="ALLOW", reason=REASON_OK, raw=data)
        return _respond("ALLOW", REASON_OK, duration_ms=800)


class DeviceRegisterView(APIView):
    """
    Регистрация/ротация device_token.
    По умолчанию rotate=True — на каждый вход приложения выдаём новый токен (вариант А).
    rotate=False позволяет привязать android_device_id без смены токена.
    Аутентификация — по пользовательскому DRF Token (пользователь должен быть залогинен в приложении).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="device-register",
        tags=["Devices"],
        request=DeviceRegisterRequestSerializer,
        responses={200: DeviceRegisterResponseSerializer},
    )
    @transaction.atomic
    def post(self, request):
        # 1) Валидация входа
        ser_in = DeviceRegisterRequestSerializer(data=request.data or {})
        ser_in.is_valid(raise_exception=True)
        rotate = ser_in.validated_data.get("rotate", True)
        android_device_id = ser_in.validated_data.get("android_device_id")

        user = request.user

        # 2) Находим или создаём устройство пользователя (простая стратегия: берём последнее активное, иначе создаём)
        device = Device.objects.filter(user=user, is_active=True).order_by("-created_at").first()
        if device is None:
            device = Device(user=user, is_active=True, name="Mobile device")

        # 3) Обновляем android_device_id при необходимости
        if android_device_id is not None:
            device.android_device_id = android_device_id

        # 4) Ротация токена: только если rotate=True (по умолчанию) или если токена нет
        if rotate:
            device.auth_token = secrets.token_hex(32)  # 64 hex символа
        elif not device.auth_token:
            # Если токена нет, создаём его даже при rotate=False
            device.auth_token = secrets.token_hex(32)

        device.save()

        # 5) Ответ клиенту
        # qr_payload — оставим простым, чтобы не ломать логику: инкапсулирует сам токен (можно заменить на свой формат)
        payload = {
            "device_id": device.id,
            "token": device.auth_token,
            "android_device_id": device.android_device_id or "",
            "qr_payload": device.auth_token,
        }
        ser_out = DeviceRegisterResponseSerializer(payload)
        return Response(ser_out.data, status=status.HTTP_200_OK)


class DeviceListMeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="device-list-me",
        tags=["Devices"],
        responses={200: DeviceMeItemSerializer(many=True)},
    )
    def get(self, request):
        items = []
        for d in Device.objects.filter(user=request.user).order_by("-created_at"):
            token = d.auth_token or ""
            preview = (token[:4] + "…" + token[-4:]) if token else ""
            items.append({
                "id": d.id,
                "android_device_id": d.android_device_id or "",
                "is_active": d.is_active,
                "token_preview": preview,
            })
        return Response(DeviceMeItemSerializer(items, many=True).data, status=status.HTTP_200_OK)


class DeviceRevokeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="device-revoke",
        tags=["Devices"],
        request=DeviceRevokeRequestSerializer,
        responses={200: DeviceRevokeResponseSerializer, 404: OpenApiResponse(description="Device not found")},
    )
    def post(self, request):
        req = DeviceRevokeRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        device = None
        if req.validated_data.get("device_id"):
            device = Device.objects.filter(pk=req.validated_data["device_id"], user=request.user).first()
        else:
            qs = Device.objects.filter(
                user=request.user,
                android_device_id=req.validated_data["android_device_id"],
            ).order_by("-created_at")
            device = qs.first()
        if not device:
            return Response({"detail":"Device not found"}, status=status.HTTP_404_NOT_FOUND)
        device.is_active = False
        device.save(update_fields=["is_active"])
        resp = {"device_id": device.id, "is_active": device.is_active}
        return Response(DeviceRevokeResponseSerializer(resp).data, status=status.HTTP_200_OK)
