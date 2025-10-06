# accessproj/settings/dev.py
from .base import *

DEBUG = True                 # в dev включаем отладку
ENV_NAME = "dev"            # чтобы /api/health возвращал понятное env

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",   # локальная SQLite вместо Postgres
    }
}

ALLOWED_HOSTS = ["*"]        # чтобы можно было ходить по IP с телефона/ESP32

# (необязательно, но удобно видеть логи в консоли)
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}