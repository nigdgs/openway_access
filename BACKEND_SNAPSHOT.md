# Backend Snapshot — 2025-10-17, commit e8dcd7f (dirty)

## Резюме (PASS/FAIL по целям)
- /auth/token: PASS (обнаружен `obtain_auth_token`; статически подтвержден маршрут)
- /access/verify: PASS (реализация, причины DENY и обработка 429 найдены в коде)
- /health|/ready: PASS (два probe-эндпоинта найдены)
- /docs и /schema: PASS (подключены Spectacular API/Swagger)
- Runtime: FAIL (pip install упал из-за SSL, см. раздел Рантайм)

## Эндпоинты (таблица)
| Метод | Путь | View | Name | Auth/Perm | Throttle(scope) | Вход | Выход | Статусы |
|---|---|---|---|---|---|---|---|---|
| GET | /health | `core.views.health` | health | AllowAny | — | — | {"status":"ok"} | 200 |
| GET | /ready | `core.views.ready` | ready | AllowAny | — | — | {"status":"ready"|"not-ready"} | 200/503 |
| GET | /docs/ | SpectacularSwaggerView | docs | AllowAny | — | — | Swagger UI | 200 |
| GET | /schema/ | SpectacularAPIView | schema | AllowAny | — | — | OpenAPI JSON | 200 |
| POST | /api/v1/auth/token | DRF `obtain_auth_token` | auth-token | AllowAny | — | username, password | {token} | 200/400 |
| POST | /api/v1/access/verify | `AccessVerifyView.post` | access-verify | None (open) | ScopedRateThrottle(access_verify) | gate_id, token | decision, reason, [duration_ms] | 200 |
| POST | /api/v1/devices/register | `DeviceRegisterView.post` | devices-register | TokenAuth + IsAuthenticated | — | rotate?, android_device_id? | device_id, token, android_device_id, qr_payload | 200 |
| GET | /api/v1/devices/me | `DeviceListMeView.get` | devices-me | TokenAuth + IsAuthenticated | — | — | список устройств | 200 |
| POST | /api/v1/devices/revoke | `DeviceRevokeView.post` | device-revoke | TokenAuth + IsAuthenticated | — | device_id? or android_device_id | device_id, is_active | 200/404 |

Ссылки на URL-конфигурации:
- ROOT: backend/core/urls.py:7-16
- API v1: backend/apps/api/v1/urls.py:1-12

## Verify: реализация и контракт
- Класс: `AccessVerifyView` (backend/apps/api/v1/views.py:47-120)
- Сериализаторы: `VerifyRequestSerializer`, `VerifyResponseSerializer` (backend/apps/api/v1/serializers.py:6-14)
- Константы: `DECISIONS`, `REASONS`, причины (backend/apps/api/v1/constants.py:1-25)
- Финальный статус-код ответа: всегда 200 OK (backend/apps/api/v1/views.py:45-46)
- Причины DENY: INVALID_REQUEST (backend/apps/api/v1/views.py:72-81), UNKNOWN_GATE (85-92), TOKEN_INVALID (93-105), NO_PERMISSION (107-115); RATE_LIMIT обрабатывается перехватом `Throttled` в `dispatch` и возвращается 200/DENY (backend/apps/api/v1/views.py:53-63)
- Throttle: `ScopedRateThrottle`, scope="access_verify" (backend/apps/api/v1/views.py:50-51)

## Settings / Env
- ROOT_URLCONF: `core.urls` (backend/accessproj/settings/base.py:39)
- DEBUG: base=False (6), dev=True (dev.py:4), prod=False (prod.py:6), test=True (test.py:3)
- ALLOWED_HOSTS: base env `DJANGO_ALLOWED_HOSTS` или `*` (base.py:7); dev `*` (dev.py:14); prod из env (prod.py:8); test `*` (test.py:4)
- DATABASES: base PostgreSQL с env `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_HOST`, `DB_PORT` (base.py:58-67); dev SQLite (dev.py:7-11); test SQLite (test.py:6-12)
- DRF DEFAULT_*: TokenAuth, IsAuthenticated, ScopedRateThrottle/User/Anon (base.py:91-109)
  - DEFAULT_THROTTLE_RATES: `access_verify` из env `ACCESS_VERIFY_RATE` либо "30/second"; `user`=1000/day; `anon`=100/day (base.py:103-109)
- CORS: `CORS_ALLOWED_ORIGINS` env с дефолтом локальных origins; `CORS_ALLOW_CREDENTIALS=True` (base.py:118-124)
- CSRF: встроенный middleware включён (base.py:33); спец-настроек нет в base/dev/test, в prod secure cookies включены (prod.py:19-23)
- LOGGING: base импортирует JSON-конфиг (base.py:125-126); dev переопределяет на консоль (dev.py:16-21); prod использует JSON (logging_json.py)
- Перечень env-переменных (только имена):
  - DJANGO_SECRET_KEY (base.py:5)
  - DJANGO_ALLOWED_HOSTS (base.py:7, prod.py:8)
  - POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD (base.py:61-63)
  - DB_HOST, DB_PORT (base.py:64-65)
  - ACCESS_VERIFY_RATE (base.py:103-105)
  - CORS_ALLOWED_ORIGINS (base.py:119-122)

## Модели/Миграции/Админ
- Ключевые модели (backend/apps/access/models.py:7-42):
  - `AccessPoint(code unique, name, location)`
  - `AccessPermission(access_point FK, user FK null, group FK null, allow)`; UniqueTogether(access_point, user, group); CheckConstraint (user or group not null); Indexes on (access_point,user) и (access_point,group)
  - `AccessEvent(access_point FK null, user FK null, device_id int nullable, decision str, reason str, raw JSON, created_at)`
- Devices (backend/apps/devices/models.py:6-14): `Device(user FK, android_device_id, auth_token unique, is_active, created_at, name, totp_secret)`
- Accounts (backend/apps/accounts/models.py:6-13): `PasswordHistory(user FK, password hash, created_at)`
- Миграции:
  - access: backend/apps/access/migrations/{0001_initial.py, 0002_accesspermission_access_acce_access__9a3b45_idx_and_more.py}
  - devices: backend/apps/devices/migrations/{0001_initial.py, 0002_auto_20250912_1225.py, 0003_alter_device_totp_secret.py}
  - accounts: backend/apps/accounts/migrations/{0001_initial.py}
- Админ (backend/apps/access/admin.py:6-23): зарегистрированы `AccessPoint`, `AccessPermission`, `AccessEvent` с list_display/filter/search; `AccessEvent` имеет readonly `created_at`, `raw`.

## URLConf
- ROOT_URLCONF указан в settings (backend/accessproj/settings/base.py:39)
- `urlpatterns` (backend/core/urls.py:7-16): health/ready, api/, schema/, docs/, admin/
- apps/api/urls (backend/apps/api/urls.py:1-5) → включает v1
- apps/api/v1/urls (backend/apps/api/v1/urls.py:1-12): access/verify, auth/token, devices/*

## Логи/среда исполнения
- LOGGING JSON (backend/accessproj/settings/logging_json.py:40-79): форматтер JSON, console handler, уровни INFO; middleware добавляет request_id и access log (backend/core/middleware.py:9-66)
- Docker Compose (backend/compose.yml:1-37): сервисы db(Postgres16) и web; db порт 5433→5432, healthcheck pg_isready; web мапит 8001→8000, healthcheck GET /healthz; зависимость web→db healthy.

## Рантайм-результаты (если были)
Шаг C1 (pip install -r requirements.txt) — FAIL. Полный вывод ошибки:
```
WARNING: Retrying ... SSLCertVerificationError('OSStatus -26276') ...
ERROR: Could not find a version that satisfies the requirement Django~=5.0.14 (from versions: none)
ERROR: No matching distribution found for Django~=5.0.14
```
Причина: SSL сертификация при доступе к PyPI (сетевое ограничение в окружении). Дальнейшие шаги (migrate, runserver, smoke) пропущены.
Как повторить локально:
```
python3 -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt
export DJANGO_SETTINGS_MODULE=accessproj.settings.dev
python backend/manage.py migrate
ACCESS_VERIFY_RATE=5/second python backend/manage.py runserver 127.0.0.1:8000
```
Если порт 8000 занят, используйте 8001.

## Гэп-анализ и Следующие шаги
- Отсутствуют рантайм-пруфы HTTP 200 для /health, /docs, /schema, /auth/token, /access/verify из-за блокирующей ошибки SSL на установке пакетов.
- Вьюхи `apps/access/views.py` пусты (backend/apps/access/views.py) — не критично для verify, но стоит проверить, нет ли исторических зависимостей.
- Проверить конфиг CORS/CSRF в prod при развёртывании за reverse proxy (prod.py:10-27).
- Убедиться, что переменные окружения для Postgres корректно прокинуты при использовании base/prod.

NEXT STEPS:
- Настроить доверенный сертификат/интернет-доступ для pip (или локальный индекс) и повторить C-шаги.
- После успешного `migrate` — создать тестовые данные (user_allow/user_deny, DRF токены, AccessPoint, AccessPermission) и провести smoke по списку из задания.
- В прод-инфре — добавить HTTPS reverse proxy перед web (см. compose nginx в ops/, если планируется).

## Приложение: Источники с ссылками
- Requirements: backend/requirements.txt:1-11; backend/requirements-dev.txt:5-24
- Settings base: backend/accessproj/settings/base.py:4-8,58-67,91-109,118-126
- Settings dev: backend/accessproj/settings/dev.py:4-21
- Settings prod: backend/accessproj/settings/prod.py:5-27
- Settings test: backend/accessproj/settings/test.py:3-28
- Core urls: backend/core/urls.py:7-16
- Health/Ready views: backend/core/views.py:7-23
- API urls: backend/apps/api/urls.py:3-5; backend/apps/api/v1/urls.py:1-12
- Verify view: backend/apps/api/v1/views.py:39-120
- Verify serializers: backend/apps/api/v1/serializers.py:6-14
- Verify constants: backend/apps/api/v1/constants.py:1-25
- Devices views: backend/apps/api/v1/views.py:123-230
- Access models/admin: backend/apps/access/models.py:7-42; backend/apps/access/admin.py:6-23
- Device model: backend/apps/devices/models.py:6-14
- Accounts model: backend/apps/accounts/models.py:6-13
- Compose: backend/compose.yml:1-37
- Logging JSON: backend/accessproj/settings/logging_json.py:40-79; Middleware: backend/core/middleware.py:9-66
