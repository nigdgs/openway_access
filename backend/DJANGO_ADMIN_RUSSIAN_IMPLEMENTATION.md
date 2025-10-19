# Django Admin Russian Localization & Model Hiding Implementation

## Summary

Successfully implemented Russian localization for Django Admin and hidden the "Devices" and "Accounts" sections from the admin interface while keeping the models functional in the codebase.

## Changes Made

### 1. Django Settings Configuration (`backend/accessproj/settings/base.py`)

**Added LocaleMiddleware:**
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.RequestIdMiddleware",
    "core.middleware.AccessLogMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # ← ADDED
    "django.middleware.common.CommonMiddleware",
    # ... rest of middleware
]
```

**Updated Language Code:**
```python
LANGUAGE_CODE = "ru"  # Changed from "ru-ru"
USE_I18N = True  # Already enabled
```

**Updated INSTALLED_APPS to use AppConfig classes:**
```python
INSTALLED_APPS = [
    # ... other apps
    "apps.accounts.apps.AccountsConfig",    # ← Updated
    "apps.devices.apps.DevicesConfig",       # ← Updated  
    "apps.access.apps.AccessConfig",        # ← Updated
    "apps.api",
]
```

### 2. App Configuration Classes

**Created `backend/apps/access/apps.py`:**
```python
from django.apps import AppConfig

class AccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.access"
    verbose_name = "Доступ"
```

**Created `backend/apps/devices/apps.py`:**
```python
from django.apps import AppConfig

class DevicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.devices"
    verbose_name = "Устройства"
```

**Updated `backend/apps/accounts/apps.py`:**
```python
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Учётные записи"  # ← ADDED

    def ready(self):
        from . import signals  # noqa
```

### 3. Model Russian Names (`backend/apps/access/models.py`)

**Added Russian verbose names to all Access models:**
```python
from django.utils.translation import gettext_lazy as _

class AccessPoint(models.Model):
    # ... fields ...
    
    class Meta:
        verbose_name = _("Точка доступа")
        verbose_name_plural = _("Точки доступа")

class AccessPermission(models.Model):
    # ... fields ...
    
    class Meta:
        verbose_name = _("Право доступа")
        verbose_name_plural = _("Права доступа")
        # ... other meta options ...

class AccessEvent(models.Model):
    # ... fields ...
    
    class Meta:
        verbose_name = _("Событие доступа")
        verbose_name_plural = _("События доступа")
        ordering = ("-created_at",)
```

### 4. Admin Hiding Module (`backend/accessproj/admin_hide.py`)

**Created comprehensive admin hiding module:**
```python
"""
Admin configuration to hide specific models from Django Admin interface.
"""

from django.contrib import admin
from django.apps import apps

def try_unregister(model_path: str):
    """Helper function to unregister a model from admin by dotted path if present."""
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
        if model:
            try:
                admin.site.unregister(model)
            except admin.sites.NotRegistered:
                pass
    except (LookupError, ValueError):
        pass

# Hide Devices section completely
try_unregister("devices.Device")

# Hide Accounts/Password history section  
try_unregister("accounts.PasswordHistory")

# Set Russian admin site headers
admin.site.site_header = "OpenWay — администрирование"
admin.site.site_title = "OpenWay"
admin.site.index_title = "Панель управления"
```

### 5. Import Hook (`backend/accessproj/__init__.py`)

**Added import to ensure admin_hide module loads at startup:**
```python
# Import side-effects to configure admin and hide models
from . import admin_hide  # noqa: F401
```

## Expected Results

After server reload, the Django Admin interface will show:

### ✅ Visible Sections:
- **Доступ** → События доступа, Права доступа, Точки доступа
- **Пользователи и группы** → Пользователи, Группы  
- **Аутентификация** → Токены

### ❌ Hidden Sections:
- ~~Устройства~~ (completely hidden)
- ~~Учётные записи~~ (completely hidden)

### ✅ Russian Interface:
- Page title: "OpenWay — администрирование"
- Site title: "OpenWay"
- Index title: "Панель управления"
- All model names in Russian
- Django's built-in Russian translations

## Testing Instructions

### 1. Start the Django Server
```bash
cd backend
# Using Docker (recommended):
docker compose up -d

# Or locally (if Django is installed):
python manage.py runserver
```

### 2. Access Admin Interface
Navigate to: `http://localhost:8001/admin/`

### 3. Verify Changes
- [ ] Language is Russian
- [ ] Page titles show "OpenWay — администрирование"
- [ ] No "Устройства" section visible
- [ ] No "Учётные записи" section visible
- [ ] "Доступ" section shows Russian model names:
  - События доступа
  - Права доступа  
  - Точки доступа

### 4. Run Django Check
```bash
python manage.py check
# Should show no errors
```

## Technical Notes

### Model Hiding Strategy
- Models are **unregistered** from admin, not deleted from codebase
- Models remain fully functional for API and other uses
- Admin interface simply doesn't show them
- Can be easily re-enabled by commenting out the unregister calls

### Localization Strategy
- Uses Django's built-in Russian translations
- Custom verbose names for models and apps
- LocaleMiddleware enables proper language switching
- All admin headers customized to Russian

### App Configuration
- Proper AppConfig classes ensure verbose names are used
- INSTALLED_APPS updated to reference AppConfig classes
- Maintains all existing functionality

## Files Modified

1. `backend/accessproj/settings/base.py` - Settings and middleware
2. `backend/apps/access/apps.py` - Access app configuration  
3. `backend/apps/devices/apps.py` - Devices app configuration
4. `backend/apps/accounts/apps.py` - Accounts app configuration
5. `backend/apps/access/models.py` - Model verbose names
6. `backend/accessproj/admin_hide.py` - Admin hiding logic (NEW)
7. `backend/accessproj/__init__.py` - Import hook

## Reverting Changes

To revert the hiding of models, simply comment out the unregister calls in `admin_hide.py`:

```python
# try_unregister("devices.Device")
# try_unregister("accounts.PasswordHistory")
```

To revert Russian localization, change `LANGUAGE_CODE` back to `"en-us"` in settings.
