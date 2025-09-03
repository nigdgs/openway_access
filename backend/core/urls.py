
from django.contrib import admin
from django.urls import path, include
from rest_framework.schemas import get_schema_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('schema/', get_schema_view(title="Access Control API", description="OpenAPI schema")),
    path('api/', include('apps.access.urls')),
    path('api/', include('apps.controllers.urls')),
    path('api/', include('apps.accounts.urls')),
]
