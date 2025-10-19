from django.apps import AppConfig


class AccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.access"
    verbose_name = "Доступ"

    def ready(self):
        from accessproj.admin_hide import configure_admin
        configure_admin()
