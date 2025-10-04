from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import health, ready

urlpatterns = [
    path("health", health, name="health"),
    path("healthz", health, name="healthz"),  # Kubernetes-style alias
    path("ready", ready, name="ready"),
    path("readyz", ready, name="readyz"),  # Kubernetes-style alias
    path("api/", include("apps.api.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("admin/", admin.site.urls),
]
