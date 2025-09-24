from django.contrib import admin
from django.urls import path, include
from apps.api.v1.views import AccessVerifyView

from .views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.api.urls")),
]

urlpatterns += [
    path("api/v1/access/verify", AccessVerifyView.as_view(), name="access-verify"),
    path("health", health, name="health"),
    path("healthz", health, name="healthz"),
]
