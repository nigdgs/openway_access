"""API application package for Django.

Exports the application config for explicit registration.
"""

# Explicit AppConfig path for older Django setups; harmless on 3.2+
default_app_config = "apps.api.apps.ApiConfig"

__all__ = ["default_app_config"]
