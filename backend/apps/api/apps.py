from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    label = "api"

    def ready(self):
        # No signals to register for now; keep startup fast
        return None
