
from django.urls import path
from .views import mobile_ticket, verify_access, events

urlpatterns = [
    path("mobile/ticket", mobile_ticket),
    path("access/verify", verify_access),
    path("events", events),
]
