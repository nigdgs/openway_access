
from django.urls import path
from .views import controller_config

urlpatterns = [
    path("controllers/config", controller_config),
]
