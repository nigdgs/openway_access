from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import AccessVerifyView, DeviceListMeView, DeviceRegisterView, DeviceRevokeView

urlpatterns = [
    path("access/verify", AccessVerifyView.as_view(), name="access-verify"),
    path("auth/token", obtain_auth_token, name="auth-token"),
    path("devices/register", DeviceRegisterView.as_view(), name="devices-register"),
    path("devices/me", DeviceListMeView.as_view(), name="devices-me"),
    path("devices/revoke", DeviceRevokeView.as_view(), name="device-revoke"),
]
