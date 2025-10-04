"""
УСТАРЕВШИЙ ФАЙЛ — НЕ ИСПОЛЬЗУЕТСЯ

ROOT_URLCONF = "core.urls" (см. accessproj/settings/base.py)

Этот файл содержал дублирующую регистрацию /api/v1/access/verify,
которая конфликтовала с правильной цепочкой:
  core.urls → apps.api.urls → apps.api.v1.urls

Оставлен для истории. Если нужна регистрация URL,
используйте только core/urls.py.
"""

from django.contrib import admin
from django.urls import include, path

from apps.api.v1.views import AccessVerifyView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.api.urls")),
    path("api/v1/access/verify", AccessVerifyView.as_view(), name="access-verify"),
]
