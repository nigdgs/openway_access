from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Simple readiness probe used by Android clients and local scripts."""
    return JsonResponse({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def ready(request):
    """Readiness probe for Kubernetes/Docker - checks DB connection."""
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1;")
        return JsonResponse({"status": "ready"})
    except Exception:
        return JsonResponse({"status": "not-ready"}, status=503)
