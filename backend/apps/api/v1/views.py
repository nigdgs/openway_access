from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, Throttled
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.db import transaction
from django.contrib.auth import get_user_model
import secrets
import time

from .serializers import (
    VerifyRequestSerializer, 
    VerifyResponseSerializer, 
    DeviceRegisterRequestSerializer, 
    DeviceRegisterResponseSerializer,
    DeviceMeItemSerializer,
    DeviceRevokeRequestSerializer,
    DeviceRevokeResponseSerializer,
)
from .constants import (
    REASON_UNKNOWN_GATE,
    REASON_TOKEN_INVALID,
    REASON_DEVICE_NOT_FOUND,
    REASON_DEVICE_INACTIVE,
    REASON_NO_PERMISSION,
    REASON_OK,
    REASON_INVALID_REQUEST,
    REASON_RATE_LIMIT,
)
from apps.access.models import AccessPoint, AccessPermission, AccessEvent
from apps.devices.models import Device
from django.contrib.auth.models import Group

User = get_user_model()

def has_access(user, access_point):
    # user or group allow
    if AccessPermission.objects.filter(access_point=access_point, user=user, allow=True).exists():
        return True
    groups = Group.objects.filter(user=user)
    if AccessPermission.objects.filter(access_point=access_point, group__in=groups, allow=True).exists():
        return True
    return False


def _respond(decision, reason, duration_ms=None):
    payload = {"decision": decision, "reason": reason}
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    ser = VerifyResponseSerializer(data=payload)
    ser.is_valid(raise_exception=True)
    return Response(ser.validated_data, status=status.HTTP_200_OK)

class AccessVerifyView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "access_verify_wifi"

    # Helpers (local)
    def _token_preview(self, tok: str | None) -> str:
        if not tok:
            return ""
        return (tok[:4] + "…" + tok[-4:]) if len(tok) > 8 else tok

    def _remote_ip(self, request):
        xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        return xff or request.META.get("REMOTE_ADDR")

    def _build_raw(self, *, request, data: dict, t0: float) -> dict:
        safe = dict(data or {})
        safe.pop("token", None)  # Удаляем полный токен из безопасных данных
        return {
            **safe,
            "transport": "wifi",
            "remote_ip": self._remote_ip(request),
            "request_id": request.headers.get("X-Request-ID") or request.META.get("HTTP_X_REQUEST_ID"),
            "token_preview": self._token_preview((data or {}).get("token")),
            "processing_ms": int((time.perf_counter() - t0) * 1000),
        }

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Throttled:
            # ScopedRateThrottle может кидать Throttled раньше, маппим в 200/DENY
            t0 = time.perf_counter()
            raw = self._build_raw(request=request, data=request.data, t0=t0)
            AccessEvent.objects.create(
                access_point=None, user=None, device_id=None,
                decision="DENY", reason=REASON_RATE_LIMIT, raw=raw
            )
            return _respond("DENY", REASON_RATE_LIMIT)

    @transaction.atomic
    def post(self, request):
        t0 = time.perf_counter()

        try:
            serializer = VerifyRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
        except Throttled:
            raw = self._build_raw(request=request, data=request.data, t0=t0)
            AccessEvent.objects.create(
                access_point=None, user=None, device_id=None,
                decision="DENY", reason=REASON_RATE_LIMIT, raw=raw
            )
            return _respond("DENY", REASON_RATE_LIMIT)

        data = serializer.validated_data

        try:
            ap = AccessPoint.objects.get(code=data["gate_id"])
        except AccessPoint.DoesNotExist:
            raw = self._build_raw(request=request, data=data, t0=t0)
            AccessEvent.objects.create(access_point=None, user=None, device_id=None,
                                       decision="DENY", reason=REASON_UNKNOWN_GATE, raw=raw)
            return _respond("DENY", REASON_UNKNOWN_GATE)

        token = data["token"]
        device = Device.objects.filter(auth_token=token).first()
        if not device:
            raw = self._build_raw(request=request, data=data, t0=t0)
            AccessEvent.objects.create(access_point=ap, user=None, device_id=None,
                                       decision="DENY", reason=REASON_TOKEN_INVALID, raw=raw)
            return _respond("DENY", REASON_TOKEN_INVALID)

        if not device.is_active:
            raw = self._build_raw(request=request, data=data, t0=t0)
            AccessEvent.objects.create(access_point=ap, user=device.user, device_id=device.id,
                                       decision="DENY", reason=REASON_DEVICE_INACTIVE, raw=raw)
            return _respond("DENY", REASON_DEVICE_INACTIVE)

        user = device.user

        if not has_access(user, ap):
            raw = self._build_raw(request=request, data=data, t0=t0)
            AccessEvent.objects.create(access_point=ap, user=user, device_id=device.id,
                                       decision="DENY", reason=REASON_NO_PERMISSION, raw=raw)
            return _respond("DENY", REASON_NO_PERMISSION)

        raw = self._build_raw(request=request, data=data, t0=t0)
        AccessEvent.objects.create(access_point=ap, user=user, device_id=device.id,
                                   decision="ALLOW", reason=REASON_OK, raw=raw)
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

    def post(self, request):
        req = DeviceRevokeRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        device = None
        if req.validated_data.get("device_id"):
            device = Device.objects.filter(pk=req.validated_data["device_id"], user=request.user).first()
        else:
            device = Device.objects.filter(user=request.user, android_device_id=req.validated_data["android_device_id"]).order_by("-created_at").first()
        if not device:
            return Response({"detail":"Device not found"}, status=status.HTTP_404_NOT_FOUND)
        device.is_active = False
        device.save(update_fields=["is_active"])
        resp = {"device_id": device.id, "is_active": device.is_active}
        return Response(DeviceRevokeResponseSerializer(resp).data, status=status.HTTP_200_OK)
