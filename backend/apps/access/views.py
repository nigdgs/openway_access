
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import time

from .serializers import VerifyRequestSerializer, EventBatchSerializer

@api_view(["POST"])
def mobile_ticket(request):
    # Демоверсия: возвращаем фиктивный session_key и exp
    exp = int(time.time()) + int(getattr(settings, "ACCESS_SESSION_TTL", 60))
    return Response({
        "user_id": "U-DEMO",
        "exp": exp,
        "session_key_b64": "ZmFrZV9zZXNzaW9uX2tleV9iYXNlNjQ=",  # "fake_session_key_base64"
        "kid": "key-2025-09-A"
    })

@api_view(["POST"])
def verify_access(request):
    ser = VerifyRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    # Демоверсия: всегда allow, если exp ещё не истёк
    now = int(time.time())
    if data["apdu"]["exp"] < now:
        return Response({"decision":"deny","reason":"expired"}, status=status.HTTP_403_FORBIDDEN)
    return Response({"decision":"allow","reason":"demo","open_seconds":3}, status=status.HTTP_200_OK)

@api_view(["POST"])
def events(request):
    ser = EventBatchSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    # TODO: сохранить в БД
    stored = len(ser.validated_data["batch"])
    return Response({"stored": stored})
