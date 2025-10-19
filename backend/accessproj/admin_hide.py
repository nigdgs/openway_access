"""
Admin configuration to hide specific models from Django Admin interface.

This module unregisters models from the admin site without removing them from the codebase.
The models remain functional but are not visible in the admin interface.
"""

from django.contrib import admin
from django.apps import apps


def try_unregister_by_label(app_label, model_name):
    """
    Helper function to unregister a model from admin by app_label and model_name.
    
    Args:
        app_label: String app label (e.g., "devices", "accounts")
        model_name: String model name (e.g., "Device", "PasswordHistory")
    """
    try:
        model = apps.get_model(app_label, model_name)
        if model:
            try:
                admin.site.unregister(model)
            except admin.sites.NotRegistered:
                pass
    except LookupError:
        # Model or app not found, ignore silently
        pass


def configure_admin():
    """
    Configure admin site with Russian headers and hide specific models.
    This function should be called after Django apps are ready.
    """
    # Hide Devices / Accounts sections
    try_unregister_by_label("devices", "Device")
    try_unregister_by_label("accounts", "PasswordHistory")

    # Set Russian admin site headers
    admin.site.site_header = "OpenWay — администрирование"
    admin.site.site_title = "OpenWay"
    admin.site.index_title = "Панель управления"
