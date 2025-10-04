from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Use SQLite for faster, isolated tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",
    }
}

# Use in-memory cache for throttling in tests (clears between tests)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
