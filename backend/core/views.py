from django.http import JsonResponse


def health(request):
    """Simple readiness probe used by Android clients and local scripts."""
    return JsonResponse({"status": "ok"})
