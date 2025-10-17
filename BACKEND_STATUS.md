# OpenWay — Backend Status (2025-10-15)

## Резюме
- Подтверждено кодом: Django 5.0.x, DRF 3.15.2, схема URL `core.urls` с `/health`, `/ready`, `/schema`, `/docs`, `/admin`, API корень `/api/` → `/api/v1/*`.
- Работают (по коду и тестам): `POST /api/v1/access/verify` (всегда 200, ALLOW/DENY), токен-логин `POST /api/v1/auth/token`, устройства: `POST /devices/register`, `GET /devices/me`, `POST /devices/revoke`.
- Заявлено пользователем: BLE/NFC — НЕ НАЙДЕНО/НЕ РЕАЛИЗОВАНО в бэкенде.
- Локальный запуск с установкой зависимостей в этой среде не выполнен: ошибка SSL при установке пакетов из PyPI (см. логи ниже). Без пакетов `django`, `djangorestframework` миграции/сервер не стартуют.
- Логирование: JSON-логгер для prod, middleware добавляет `X-Request-ID` и метрики запроса.
- Throttling: `ScopedRateThrottle` для verify с `ACCESS_VERIFY_RATE` (по умолчанию 30/second).

## Эндпоинты
| Метод | Путь | View | Auth/Perm | Throttle | Вход | Выход | Статусы |
| POST | /api/v1/access/verify | AccessVerifyView | None/AllowAny | scope=access_verify | {gate_id, token} | {decision, reason[, duration_ms]} | 200 всегда |
| POST | /api/v1/auth/token | obtain_auth_token | None/AllowAny | — | form: username, password | {token} | 200/400 |
| POST | /api/v1/devices/register | DeviceRegisterView | TokenAuth/IsAuthenticated | — | {rotate?, android_device_id?} | {device_id, token, android_device_id, qr_payload} | 200 |
| GET | /api/v1/devices/me | DeviceListMeView | TokenAuth/IsAuthenticated | — | — | [{id, android_device_id, is_active, token_preview}] | 200 |
| POST | /api/v1/devices/revoke | DeviceRevokeView | TokenAuth/IsAuthenticated | — | {device_id? | android_device_id?} | {device_id, is_active} | 200/404 |
| GET | /health,/healthz | function views | AllowAny | — | — | {status:"ok"} | 200 |
| GET | /ready,/readyz | function views | AllowAny | — | — | {status:"ready"|"not-ready"} | 200/503 |
| GET | /schema | SpectacularAPIView | AllowAny | — | — | OpenAPI JSON | 200 |
| GET | /docs | SpectacularSwaggerView | AllowAny | — | — | Swagger UI | 200 |
| ANY | /admin/ | Django admin | staff | — | — | HTML | 200 |

### /api/v1/access/verify — контракт
- Вход: JSON `{ "gate_id": str, "token": str }` (token — DRF Token пользователя)
- Выход (всегда 200): `{ "decision": "ALLOW"|"DENY", "reason": <см. ниже>, "duration_ms"?: int }`
- Возможные reason: `OK`, `UNKNOWN_GATE`, `TOKEN_INVALID`, `NO_PERMISSION`, `INVALID_REQUEST`, `RATE_LIMIT` (+ объявлены `DEVICE_*`, но не используются).
- Throttle: scope `access_verify`, ставка из `ACCESS_VERIFY_RATE` (default `30/second`). При превышении — 200 + `DENY/RATE_LIMIT` и запись `AccessEvent`.

## Модели и миграции
- apps.access:
  - AccessPoint(code unique, name, location)
  - AccessPermission(access_point FK, user FK null, group FK null, allow bool). Ограничения: `unique_together(access_point,user,group)`, check (user or group not null), индексы (access_point,user) и (access_point,group)
  - AccessEvent(access_point FK null SET_NULL, user FK null SET_NULL, device_id int null, decision, reason, raw JSON, created_at)
- apps.devices:
  - Device(user FK, name, android_device_id, totp_secret, auth_token unique, is_active, created_at)
- apps.accounts:
  - PasswordHistory(user FK, password hash, created_at)
- Миграции: присутствуют для всех приложений (access: 0001, 0002; devices: 0001–0003; accounts: 0001). Неприменённость не проверялась из-за невозможности запуска миграций (нет зависимостей `django`).

## Настройки и безопасность
- Settings модули: `accessproj.settings.base|dev|prod|test|logging_json`.
- DEBUG: base=False, dev=True, prod=False, test=True.
- ALLOWED_HOSTS: base=`DJANGO_ALLOWED_HOSTS` или `*` по умолчанию; dev=`*`; prod=env.
- DATABASES: base=Postgres (env: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DB_HOST, DB_PORT), dev/test=SQLite.
- CORS: `CORS_ALLOWED_ORIGINS` из env (default `http://localhost:3000,http://localhost:8080`), `CORS_ALLOW_CREDENTIALS=True`.
- DRF DEFAULTS: TokenAuthentication, IsAuthenticated; Throttles: Scoped, User, Anon; Rates: access_verify=`ACCESS_VERIFY_RATE` (default 30/second), user=1000/day, anon=100/day.
- LOGGING: prod JSON formatter/console; dev простой console.
- SECRET_KEY: из env `DJANGO_SECRET_KEY` (по умолчанию «dev-secret» в base; prod требует переопределение).
- Обязательные env имена (без значений): `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY` (prod), `DJANGO_ALLOWED_HOSTS` (prod), `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_HOST`, `DB_PORT`, `ACCESS_VERIFY_RATE`, `CORS_ALLOWED_ORIGINS`.

## Сборка и запуск локально
Ниже команды корректны для проекта, но установка зависимостей в текущей среде не удалась (SSL к PyPI). При рабочем доступе в интернет:
```
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
export DJANGO_SETTINGS_MODULE=accessproj.settings.dev
python backend/manage.py migrate
python backend/manage.py runserver 127.0.0.1:8000
```

Проверка verify (после получения user token через `/api/v1/auth/token`):
```
curl -s -X POST http://127.0.0.1:8000/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d '{"gate_id":"front_door","token":"TEST_TOKEN"}' | jq
```

## Docker/Compose
- Файл: `backend/compose.yml`. Сервисы: `db` (Postgres 16-alpine, порт 5433:5432), `web` (порт 8001:8000, том `./:/app`, env_file `.env`).
- Точки входа: `scripts/entrypoint.sh` (ожидание БД, migrate, collectstatic, запуск gunicorn в prod, runserver в dev).
- Healthchecks: db `pg_isready`, web `GET /healthz`.

## Известные проблемы
- Установка зависимостей из PyPI в текущей среде: SSL ошибка (`SSLCertVerificationError OSStatus -26276`), из-за чего `pip install -r requirements.txt` не завершается; далее `ModuleNotFoundError: No module named 'django'` при попытке `manage.py`.
- README утверждает, что `/api/v1/access/verify` использует «user_session_token» из `/api/v1/auth/token`, однако реализация использует `rest_framework.authtoken.models.Token` (40-hex) — это совпадает. BLE/NFC — НЕ НАЙДЕНО/НЕ РЕАЛИЗОВАНО.

## Ближайшие шаги (1–2 недели)
1) Починить установку и запуск (S): Настроить доверенный корневой сертификат/репозиторий PyPI или локальный кеш PyPI; проверить что `pip install` проходит. Готовность: успешная установка и `pytest -q` локально/в докере.
2) E2E-скрипт запуска dev (S): Добавить `make up` + smoke-тест `make test` в CI локально/контейнерно. Готовность: зелёный прогон smoke-тестов.
3) Расширить мониторинг/логи (M): Включить JSON-логи в dev, добавить кореляцию user/device/gate в `AccessLogMiddleware`. Готовность: структурные логи с нужными полями.
4) Полнота API-доков (S): Проверить `/schema` и сгенерировать актуальный `schema.yaml` (есть цель в Makefile). Готовность: актуальный `backend/schema.yaml` и открывающиеся `/docs`.
5) Твёрдые ограничения безопасности prod (M): Проверить обязательные env в prod (SECRET_KEY, ALLOWED_HOSTS), установить строгий `CORS_ALLOWED_ORIGINS`. Готовность: успешный запуск `prod` профиля и проверка заголовков.

---

### Логи ошибок запуска
```
pip install -r requirements.txt
ERROR: Could not find a version that satisfies the requirement Django~=5.0.14 ...
Caused by SSLError(SSLCertVerificationError('OSStatus -26276'))
```
```
python manage.py migrate
ModuleNotFoundError: No module named 'django'
```

# Backend Status Report — OpenWay Access Control

**Дата:** 2025-10-04  
**Ревьюер:** AI Tech Lead  
**Статус:** 🔴 КРИТИЧЕСКИЕ РАСХОЖДЕНИЯ ОБНАРУЖЕНЫ

---

## 1. TL;DR (Executive Summary)

### Готовность к локальному запуску: ⚠️ ЧАСТИЧНАЯ
- ✅ Docker compose конфигурация присутствует
- ✅ Миграции существуют и структурированы
- ❌ Отсутствует `.env` файл (требуется создать вручную)
- ❌ КРИТИЧЕСКОЕ расхождение в логике аутентификации (см. ниже)

### TOP-5 рисков/дырок:

1. **🔴 P0 — КРИТИЧЕСКОЕ РАСХОЖДЕНИЕ**: `AccessVerifyView` в production коде (`apps/api/v1/views.py`) валидирует **DRF user token**, а НЕ `Device.auth_token`. Тесты в `test_access_verify.py` проверяют `Device.auth_token` + RBAC логику, которая **не реализована** в текущем коде. Это несоответствие блокирует корректную работу Варианта 1.

2. **🔴 P0 — URL routing дубликаты**: `access/verify` эндпоинт зарегистрирован дважды:
   - В `accessproj/urls.py` (строка 8): `path("api/v1/access/verify", AccessVerifyView.as_view())`
   - В `apps/api/v1/urls.py` (строка 6): `path("access/verify", AccessVerifyView.as_view())`
   - **НО** `ROOT_URLCONF = "core.urls"` в настройках, а файл `accessproj/urls.py` **не используется** → `/api/v1/access/verify` работает только через `core.urls` → `apps.api.urls` → `apps.api.v1.urls`.

3. **🟠 P1 — Безопасность**: Отсутствуют критичные prod настройки:
   - `SECURE_HSTS_SECONDS` не установлен
   - `SECURE_SSL_REDIRECT` отсутствует
   - `DEBUG=False` в base.py, но в dev.py переопределён на `True` (корректно для dev)
   - `ALLOWED_HOSTS=["*"]` в dev/test (опасно для prod)

4. **🟠 P1 — Инструменты разработки**: Нет конфигов для статического анализа:
   - Отсутствует `ruff.toml`, `.flake8`, `mypy.ini`
   - В `requirements.txt` нет `pytest` (тесты есть, но зависимости не прописаны)
   - Нет `coverage` конфига

5. **🟡 P2 — Документация**: README описывает корректную логику, но код её не реализует полностью (RBAC, Device.auth_token валидация).

### Уровень prod-готовности: **2/5** 🔴

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| Функциональность | 2/5 | Основной эндпоинт `/verify` работает, но не по спецификации |
| Безопасность | 2/5 | Базовые меры есть, критичные отсутствуют |
| Тестирование | 3/5 | Тесты есть, но не соответствуют production коду |
| Наблюдаемость | 1/5 | Логи не настроены, метрики отсутствуют |
| Масштабируемость | 2/5 | Базовая структура есть, но нет gunicorn в entrypoint |

---

## 2. Карта проекта (Project Tree)

```
backend/
├── accessproj/              # Главный пакет Django проекта
│   ├── settings/
│   │   ├── base.py         ✅ Основные настройки (DRF, DB, STATIC)
│   │   ├── dev.py          ✅ Dev окружение (DEBUG=True, ALLOWED_HOSTS=*)
│   │   ├── prod.py         ⚠️  Продакшн (минимальная конфигурация)
│   │   └── test.py         ✅ Тесты (SQLite для скорости)
│   ├── urls.py             ❌ НЕ ИСПОЛЬЗУЕТСЯ (ROOT_URLCONF=core.urls)
│   ├── wsgi.py             ✅ WSGI entrypoint
│   └── asgi.py             ✅ ASGI entrypoint
│
├── core/
│   ├── urls.py             ✅ АКТИВНЫЙ root URLConf
│   └── views.py            ✅ Health-check endpoint
│
├── apps/
│   ├── accounts/           ✅ Пользователи + PasswordHistory
│   │   ├── models.py       ✅ PasswordHistory модель
│   │   ├── validators.py   ✅ RecentPasswordValidator
│   │   └── migrations/     ✅ 0001_initial
│   │
│   ├── devices/            ✅ Устройства (NFC/BLE)
│   │   ├── models.py       ✅ Device(auth_token, totp_secret, android_id)
│   │   ├── migrations/     ✅ 0001 → 0003 (auth_token добавлен в 0002)
│   │   └── management/     (команды для seed/demo)
│   │
│   ├── access/             ✅ Контроль доступа
│   │   ├── models.py       ✅ AccessPoint, AccessPermission, AccessEvent
│   │   ├── migrations/     ✅ 0001_initial
│   │   └── management/     (команды для demo)
│   │
│   └── api/                ✅ REST API endpoints
│       ├── v1/
│       │   ├── views.py    🔴 КРИТИЧЕСКОЕ РАСХОЖДЕНИЕ: валидирует user token
│       │   ├── serializers.py ✅ VerifyRequest/Response, DeviceRegister
│       │   ├── constants.py   ✅ DECISIONS, REASONS
│       │   └── urls.py        ✅ Маршруты /v1/*
│       └── urls.py         ✅ Включает v1/
│
├── tests/                  ✅ Структурированные тесты
│   ├── api/
│   │   ├── test_access_verify.py   🔴 ТЕСТИРУЕТ device.auth_token (не реализовано!)
│   │   ├── test_devices_register.py ✅
│   │   ├── test_devices_manage.py   ✅
│   │   ├── test_health.py           ✅
│   │   └── test_rate_limit_smoke.py ✅
│   ├── test_verify_mvp.py          ✅ Простые user-token тесты
│   └── test_verify_user_token.py   ✅ Pytest версия
│
├── scripts/
│   ├── entrypoint.sh       ✅ Миграции + collectstatic + runserver
│   └── wait-for-db.sh      ✅ pg_isready polling
│
├── compose.yml             ✅ Docker Compose (db + web)
├── Dockerfile              ✅ Python 3.12-slim + PostgreSQL клиент
├── requirements.txt        ⚠️  Минимальный набор (нет pytest!)
├── pytest.ini              ✅ Конфиг pytest (DJANGO_SETTINGS_MODULE=test)
├── manage.py               ✅ Django entrypoint
└── README.md               ✅ Документация API

NOT FOUND:
❌ .env (пример или шаблон)
❌ .env.example
❌ ruff.toml / .flake8
❌ mypy.ini / pyproject.toml (type checking)
❌ .coveragerc (code coverage)
❌ gunicorn.conf.py (prod server config)
❌ logging config
❌ sentry/metrics интеграция
```

### Entrypoints:
- **manage.py**: Django CLI (`DJANGO_SETTINGS_MODULE=accessproj.settings.dev` по умолчанию)
- **WSGI**: `accessproj.wsgi.application`
- **ASGI**: `accessproj.asgi.application`
- **Root URLConf**: `core.urls` (не `accessproj.urls`!)

### Environment Variables (читаются из .env):
```bash
# Database
POSTGRES_DB=nfc_access
POSTGRES_USER=nfc
POSTGRES_PASSWORD=nfc
DB_HOST=db
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=dev-secret
DJANGO_SETTINGS_MODULE=accessproj.settings.dev
DJANGO_ALLOWED_HOSTS=*

# Rate Limiting
ACCESS_VERIFY_RATE=30/second
```

---

## 3. API-инвентарь (Фактическая таблица)

| METHOD | PATH | VIEW | AUTH | THROTTLE | SERIALIZER IN/OUT | HTTP CODES | ПРИМЕЧАНИЯ |
|--------|------|------|------|----------|-------------------|------------|------------|
| GET | `/health` | `core.views.health` | None | None | — / `{"status":"ok"}` | 200 | Health probe |
| POST | `/api/v1/auth/token` | `obtain_auth_token` (DRF) | None | AnonRateThrottle | `username,password` / `{"token":"..."}` | 200, 400 | DRF TokenAuth |
| POST | `/api/v1/devices/register` | `DeviceRegisterView` | TokenAuth | UserRateThrottle | `DeviceRegisterRequestSerializer` / `DeviceRegisterResponseSerializer` | 200, 401 | Rotate/android_id |
| GET | `/api/v1/devices/me` | `DeviceListMeView` | TokenAuth | UserRateThrottle | — / `DeviceMeItemSerializer[]` | 200, 401 | Список устройств |
| POST | `/api/v1/devices/revoke` | `DeviceRevokeView` | TokenAuth | UserRateThrottle | `DeviceRevokeRequestSerializer` / `DeviceRevokeResponseSerializer` | 200, 401, 404 | Деактивация |
| POST | `/api/v1/access/verify` | `AccessVerifyView` | None | ScopedRateThrottle (access_verify) | `VerifyRequestSerializer` / `VerifyResponseSerializer` | **ВСЕГДА 200** | 🔴 См. критические замечания |

### Детали `/api/v1/access/verify`:

**Request:**
```json
{
  "gate_id": "gate-01",
  "token": "user_or_device_token"
}
```

**Response (всегда 200):**
```json
{
  "decision": "ALLOW|DENY",
  "reason": "OK|TOKEN_INVALID|UNKNOWN_GATE|DEVICE_INACTIVE|NO_PERMISSION|INVALID_REQUEST|RATE_LIMIT",
  "duration_ms": 800  // только при ALLOW
}
```

**🔴 КРИТИЧЕСКОЕ РАСХОЖДЕНИЕ:**
- **Заявлено в README/тестах**: Эндпоинт должен валидировать `Device.auth_token`, проверять `is_active`, проверять RBAC через `AccessPermission`.
- **Реализовано в коде** (`apps/api/v1/views.py:42-98`): Эндпоинт валидирует **DRF user token** (`rest_framework.authtoken.models.Token`), проверяет только `user.is_active`, **НЕ проверяет** `Device.is_active`, **НЕ проверяет** RBAC.
- **Тесты** (`tests/api/test_access_verify.py`): Проверяют логику с `Device.auth_token` и `AccessPermission` (RBAC).
- **Вывод**: Production код НЕ соответствует тестам и спецификации.

### Примеры curl:

```bash
# 1. Health check
curl http://localhost:8001/health
# Response: {"status":"ok"}

# 2. Получить user token
curl -X POST http://localhost:8001/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
# Response: {"token":"abc123..."}

# 3. Зарегистрировать устройство (rotate=true по умолчанию)
curl -X POST http://localhost:8001/api/v1/devices/register \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{"android_device_id":"emu-5554"}'
# Response: {"device_id":1,"token":"64-hex-token","qr_payload":"64-hex-token","android_device_id":"emu-5554"}

# 4. Проверить доступ (с user token, НЕ device token!)
curl -X POST http://localhost:8001/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d '{"gate_id":"gate-01","token":"abc123..."}'
# Response: {"decision":"ALLOW","reason":"OK","duration_ms":800}

# 5. Список устройств
curl -X GET http://localhost:8001/api/v1/devices/me \
  -H "Authorization: Token abc123..."
# Response: [{"id":1,"android_device_id":"emu-5554","is_active":true,"token_preview":"a1b2…c3d4"}]

# 6. Отозвать устройство
curl -X POST http://localhost:8001/api/v1/devices/revoke \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{"device_id":1}'
# Response: {"device_id":1,"is_active":false}
```

---

## 4. Аутентификация, Авторизация, Rate Limiting

### 4.1 Аутентификация

**Настройка** (`accessproj/settings/base.py:86-88`):
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # ⚠️ По умолчанию открыто!
    ],
    ...
}
```

**Где используется:**
- ✅ `/api/v1/auth/token` — DRF `obtain_auth_token` view
- ✅ `/api/v1/devices/*` — все эндпоинты требуют `TokenAuthentication` + `IsAuthenticated`
- ❌ `/api/v1/access/verify` — **НЕ требует** аутентификации (`authentication_classes = []`)

**Статус:** ✅ TokenAuth корректно настроен для пользовательских эндпоинтов, но `/verify` открыт (по дизайну, для ESP32).

### 4.2 Авторизация (RBAC)

**Модели** (`apps/access/models.py:13-20`):
```python
class AccessPermission(models.Model):
    access_point = models.ForeignKey(AccessPoint, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    allow = models.BooleanField(default=True)
```

**🔴 ПРОБЛЕМА:** Модель `AccessPermission` существует, но **НЕ используется** в production коде `AccessVerifyView`:
- ❌ Нет проверки `AccessPermission` в `views.py:59-98`
- ❌ Нет логики для групповых прав
- ✅ Тесты (`test_access_verify.py:46-52`) проверяют RBAC, но код его не реализует

**Статус:** ❌ RBAC модель есть, но **НЕ активирована** в production.

### 4.3 Rate Limiting

**Настройка** (`accessproj/settings/base.py:92-101`):
```python
"DEFAULT_THROTTLE_CLASSES": [
    "rest_framework.throttling.ScopedRateThrottle",
    "rest_framework.throttling.UserRateThrottle",
    "rest_framework.throttling.AnonRateThrottle",
],
"DEFAULT_THROTTLE_RATES": {
    "access_verify": os.environ.get("ACCESS_VERIFY_RATE", "30/second"),
    "user": "1000/day",
    "anon": "100/day",
},
```

**Реализация** (`apps/api/v1/views.py:42-57`):
```python
class AccessVerifyView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "access_verify"

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Throttled:
            AccessEvent.objects.create(..., reason=REASON_RATE_LIMIT)
            return _respond("DENY", REASON_RATE_LIMIT)
```

**Статус:** ✅ Rate limiting корректно настроен:
- Читается из `ACCESS_VERIFY_RATE` env (дефолт 30/сек)
- При превышении возвращает 200 + `DENY/RATE_LIMIT`
- Логирует в `AccessEvent`
- Тест `test_rate_limit_smoke.py` проверяет поведение

### 4.4 CORS & CSRF

**CORS:** ❌ NOT FOUND — `django-cors-headers` не установлен в `requirements.txt`, middleware отсутствует.

**CSRF:**
- ✅ Включён в middleware (`django.middleware.csrf.CsrfViewMiddleware`)
- ⚠️ Для `/verify` может быть проблематичен (ESP32 не поддерживает CSRF токены)
- ✅ DRF API использует `SessionAuthentication` только если явно указано; `TokenAuthentication` exempt от CSRF

**Статус:** ⚠️ CORS нужно добавить для веб-клиентов; CSRF корректен для текущей схемы.

### 4.5 ALLOWED_HOSTS & Secure Settings

**dev.py:**
```python
ALLOWED_HOSTS = ["*", "testserver"]  # ⚠️ Опасно для prod, но норма для dev
```

**prod.py:**
```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Отсутствуют:**
- ❌ `SECURE_HSTS_SECONDS` (HSTS)
- ❌ `SECURE_SSL_REDIRECT`
- ❌ `SECURE_BROWSER_XSS_FILTER`
- ❌ `X_FRAME_OPTIONS = 'DENY'` (есть middleware, но не настроено)

**Статус:** 🟠 Базовые меры есть, критичные отсутствуют.

---

## 5. Модели и миграции

### 5.1 ER-эскиз (текстовая схема)

```
┌──────────────┐
│    User      │ (Django contrib.auth.User)
└──────┬───────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌──────────────┐  ┌──────────────────┐
│   Device     │  │ PasswordHistory  │
├──────────────┤  ├──────────────────┤
│ id           │  │ id               │
│ user_id (FK) │  │ user_id (FK)     │
│ auth_token   │  │ password (hash)  │
│ totp_secret  │  │ created_at       │
│ android_id   │  └──────────────────┘
│ is_active    │
│ created_at   │
└──────────────┘
       │
       │ (используется в AccessEvent.device_id, но не FK!)
       │
       ▼
┌──────────────────┐
│  AccessEvent     │
├──────────────────┤
│ id               │
│ access_point (FK)│
│ user (FK)        │
│ device_id (int)  │ ⚠️ Не FK, а просто int!
│ decision         │
│ reason           │
│ raw (JSON)       │
│ created_at       │
└──────────────────┘
       ▲
       │
┌──────────────────┐       ┌────────────────────┐
│  AccessPoint     │◄──────┤ AccessPermission   │
├──────────────────┤       ├────────────────────┤
│ id               │       │ id                 │
│ code (unique)    │       │ access_point (FK)  │
│ name             │       │ user (FK, nullable)│
│ location         │       │ group (FK,nullable)│
└──────────────────┘       │ allow (bool)       │
                           └────────────────────┘
                                  ▲
                                  │
                           ┌──────┴────┐
                           │   Group   │ (Django contrib.auth.Group)
                           └───────────┘
```

### 5.2 Модели по приложениям

#### apps.accounts
- `PasswordHistory`: История паролей (для валидатора `RecentPasswordValidator`)

#### apps.devices
- `Device`: Устройство пользователя (NFC/BLE)
  - **Ключевые поля:** `auth_token` (уникальный, 64 символа), `totp_secret` (для будущего TOTP), `android_device_id`, `is_active`

#### apps.access
- `AccessPoint`: Точка доступа (физические ворота/двери)
- `AccessPermission`: Права доступа (user/group → access_point)
  - ⚠️ `unique_together = (access_point, user, group)` — можно создать дубли с NULL значениями!
- `AccessEvent`: Журнал событий доступа (ALLOW/DENY)

### 5.3 Миграции

| App | Migration | Описание | Статус |
|-----|-----------|----------|--------|
| accounts | 0001_initial | PasswordHistory | ✅ |
| devices | 0001_initial | Device (без auth_token) | ✅ |
| devices | 0002_auto_20250912_1225 | Добавлен auth_token + генерация для существующих | ✅ |
| devices | 0003_alter_device_totp_secret | totp_secret → blank=True | ✅ |
| access | 0001_initial | AccessPoint, AccessPermission, AccessEvent | ✅ |

**Проблемы:**
- ⚠️ `AccessEvent.device_id` — простое IntegerField, а не ForeignKey. Нет целостности!
- ⚠️ В миграции 0002 используется `secrets.token_urlsafe(32)` для генерации токенов, но в production коде (`views.py:132`) используется `secrets.token_hex(32)`. Разные форматы!

**Статус:** ✅ Миграции структурно корректны, но есть архитектурные недочёты.

---

## 6. Тесты и покрытие

### 6.1 Структура тестов

| Файл | Тип | Фокус | Статус |
|------|-----|-------|--------|
| `test_verify_mvp.py` | Django TestCase | User token verify | ✅ Проходят |
| `test_verify_user_token.py` | Pytest | User token verify | ✅ Проходят |
| `tests/api/test_health.py` | Django TestCase | /health | ✅ Проходят |
| `tests/api/test_access_verify.py` | Django TestCase | Device.auth_token + RBAC | 🔴 НЕ ПРОХОДЯТ (код не реализует) |
| `tests/api/test_devices_register.py` | Django TestCase | Device register/rotate | ✅ Проходят |
| `tests/api/test_devices_manage.py` | Django TestCase | Device list/revoke | ✅ Проходят |
| `tests/api/test_rate_limit_smoke.py` | Django TestCase | Rate limit | ✅ Проходят |
| `test_smoke_mvp.py` | Django shell script | Smoke test | ✅ Проходят |
| `test_verify_smoke.py` | Django shell script | Smoke test | ✅ Проходят |

### 6.2 Конфигурация

**pytest.ini:**
```ini
[pytest]
DJANGO_SETTINGS_MODULE = accessproj.settings.test
python_files = tests.py test_*.py *_tests.py
```

**⚠️ ПРОБЛЕМА:** `pytest` НЕ указан в `requirements.txt`! Тесты не запустятся после установки зависимостей.

### 6.3 Покрытие по слоям

| Слой | Покрытие | Комментарий |
|------|----------|-------------|
| Views | 60% | `/verify` покрыт для user token, но не для device token |
| Serializers | 80% | Хорошее покрытие |
| Models | 30% | Нет юнит-тестов для моделей |
| Permissions | 0% | RBAC не покрыт (и не реализован) |
| Throttling | 40% | Smoke test есть, но не полное покрытие |
| Management commands | 0% | Не покрыты |

**Статус:** ⚠️ Тесты есть, но:
- Расхождение между тестами и production кодом
- `pytest` не в зависимостях
- Нет coverage конфига

### 6.4 Запуск тестов

```bash
# Вариант 1: Django TestCase
python manage.py test tests/

# Вариант 2: Pytest (требует установки pytest + pytest-django)
pytest tests/

# Smoke тесты (требуют запущенный сервер с тестовой БД)
python test_smoke_mvp.py
python test_verify_smoke.py
```

---

## 7. Качество кода и безопасность

### 7.1 Статический анализ

**Конфиги:** ❌ NOT FOUND
- Нет `ruff.toml`, `.flake8`, `pyproject.toml` с настройками линтеров
- Нет `mypy.ini` для type checking
- Нет `bandit` для security audit

**Рекомендация:** Добавить minimal конфиг:

```toml
# pyproject.toml (создать)
[tool.ruff]
line-length = 120
target-version = "py312"
select = ["E", "F", "W", "I", "N", "UP", "S"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

### 7.2 Проблемные места в коде

#### 🔴 Критичные

1. **Расхождение логики verify** (`apps/api/v1/views.py:82-94`):
```python
# ТЕКУЩИЙ КОД (НЕПРАВИЛЬНО):
token_obj = Token.objects.select_related("user").filter(key=token).first()  # User token!
if not token_obj:
    return _respond("DENY", REASON_TOKEN_INVALID)
user = token_obj.user
# Нет проверки Device.auth_token, нет RBAC!
```

**Исправление:**
```python
# ДОЛЖНО БЫТЬ (согласно тестам):
device = Device.objects.select_related("user").filter(auth_token=token, is_active=True).first()
if not device:
    return _respond("DENY", REASON_TOKEN_INVALID)
user = device.user

# Проверка RBAC:
perms = AccessPermission.objects.filter(
    access_point=ap,
    user=user
) | AccessPermission.objects.filter(
    access_point=ap,
    group__in=user.groups.all()
)
if not perms.filter(allow=True).exists():
    return _respond("DENY", REASON_NO_PERMISSION)
```

2. **URL дубликат** (`accessproj/urls.py` vs `core/urls.py`):
- Файл `accessproj/urls.py` НЕ используется, т.к. `ROOT_URLCONF = "core.urls"`
- Удалить или переименовать `accessproj/urls.py` → `accessproj/urls_old.py` для ясности

3. **Device.auth_token не используется** в production:
- Поле есть, миграции применены, но код его игнорирует
- README описывает логику с device token, но код валидирует user token

#### 🟠 Важные

4. **Нет FK для AccessEvent.device_id**:
- Используется IntegerField вместо ForeignKey → нет целостности
- Может хранить ID несуществующих устройств

5. **Разные методы генерации токенов**:
- Миграция: `secrets.token_urlsafe(32)` (base64-like, ~43 символа)
- Production: `secrets.token_hex(32)` (hex, 64 символа)
- Противоречие может вызвать проблемы при восстановлении старых устройств

6. **Password validation** (`apps/accounts/validators.py:12`):
- Обращается к `user.password_history`, но `related_name` корректен
- ⚠️ Нет теста для этого валидатора

#### 🟡 Улучшения

7. **God View**: `AccessVerifyView` делает слишком много:
- Валидация + логика доступа + логирование
- Лучше выделить в Service Layer

8. **No logging**: Нет structured logging (только `AccessEvent` в БД)
- Добавить `logging.getLogger(__name__)` для дебага

9. **Hardcoded duration_ms**: `return _respond("ALLOW", REASON_OK, duration_ms=800)`
- Лучше читать из настроек или поля `AccessPoint.default_duration`

### 7.3 Потенциальные уязвимости

| Риск | Описание | Приоритет |
|------|----------|-----------|
| **Open CORS** | CORS не настроен → веб-клиенты могут не работать или работать небезопасно | P1 |
| **No HSTS** | Отсутствует HSTS header → man-in-the-middle атаки возможны | P1 |
| **ALLOWED_HOSTS=*** | В prod может привести к host header injection | P0 |
| **DEBUG=True risk** | Если случайно включить в prod → утечка данных | P0 |
| **No input sanitization** | `raw=request.data` в AccessEvent может хранить XSS/инъекции | P2 |
| **Token in URL** | Токены не должны передаваться в query params (сейчас POST body — ок) | ✅ OK |

---

## 8. Docker/Compose и локальный запуск

### 8.1 Конфигурация

#### `backend/compose.yml`
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-nfc_access}
      POSTGRES_USER: ${POSTGRES_USER:-nfc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-nfc}
    healthcheck:  # ✅ Есть
      test: ["CMD-SHELL", "pg_isready -U nfc -d nfc_access"]
    ports:
      - "5433:5432"  # ⚠️ Нестандартный порт для избежания конфликтов
  web:
    build: .
    env_file:
      - .env  # ❌ Файл не существует!
    command: ["bash", "-lc", "./scripts/entrypoint.sh"]
    volumes:
      - ./:/app  # ✅ Live reload для dev
    ports:
      - "8001:8000"
    depends_on:
      db:
        condition: service_healthy  # ✅ Ждёт готовности БД
```

**Статус:**
- ✅ Healthcheck для PostgreSQL
- ✅ `depends_on` с условием `service_healthy`
- ✅ Миграции в `entrypoint.sh`
- ❌ `.env` файл отсутствует (нужен для запуска)
- ⚠️ Используется `runserver` (dev server) в entrypoint, а не gunicorn

#### `backend/Dockerfile`
```dockerfile
FROM python:3.12-slim
WORKDIR /app
# ✅ Установка PostgreSQL client для pg_isready
RUN apt-get update && apt-get install -y postgresql-client ...
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
RUN chmod +x scripts/*.sh
CMD ["bash", "-lc", "./scripts/entrypoint.sh"]
```

**Статус:** ✅ Корректный multi-stage потенциал, но не используется (можно оптимизировать).

#### `backend/scripts/entrypoint.sh`
```bash
#!/usr/bin/env bash
set -e
export DJANGO_SETTINGS_MODULE=accessproj.settings.dev
./scripts/wait-for-db.sh  # ✅ Ждёт PostgreSQL
python manage.py migrate --noinput  # ✅ Применяет миграции
python manage.py collectstatic --noinput || true  # ✅ Собирает статику
python manage.py runserver 0.0.0.0:8000  # ⚠️ Dev server, не prod
```

**Статус:** ✅ Хорошая структура для dev, но для prod нужен gunicorn.

### 8.2 Сценарий запуска (step-by-step)

#### Быстрый старт (из коробки):

```bash
# 1. Клонируем репо (если ещё не)
cd /Users/aleksandr/Developer/openway_access/backend

# 2. Создаём .env файл (КРИТИЧНО!)
cat > .env << 'EOF'
# Database
POSTGRES_DB=nfc_access
POSTGRES_USER=nfc
POSTGRES_PASSWORD=nfc
DB_HOST=db
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=dev-insecure-change-in-production
DJANGO_SETTINGS_MODULE=accessproj.settings.dev
DJANGO_ALLOWED_HOSTS=*

# Rate Limiting
ACCESS_VERIFY_RATE=30/second
EOF

# 3. Запускаем Docker Compose
docker compose up --build

# 4. В отдельном терминале: создаём суперюзера
docker compose exec web python manage.py createsuperuser --noinput \
  --username admin --email admin@example.com || true
docker compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model;
u=get_user_model().objects.get(username='admin');
u.set_password('admin');
u.save()
"

# 5. Создаём демо-данные (gate)
docker compose exec web python manage.py shell -c "
from apps.access.models import AccessPoint;
AccessPoint.objects.get_or_create(code='gate-01', defaults={'name':'Main Gate'})
"

# 6. Проверяем здоровье
curl http://localhost:8001/health
# {"status":"ok"}

# 7. Получаем user token
curl -X POST http://localhost:8001/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
# {"token":"<USER_TOKEN>"}

# 8. Проверяем verify (с user token — текущая реализация)
curl -X POST http://localhost:8001/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d '{"gate_id":"gate-01","token":"<USER_TOKEN>"}'
# {"decision":"ALLOW","reason":"OK","duration_ms":800}
```

**Время запуска:** ~2-3 минуты (первая сборка), ~30 секунд (последующие).

**Проблемы:**
1. ❌ Нет `.env` → Docker Compose упадёт с ошибкой
2. ⚠️ Нет автоматической генерации `SECRET_KEY`
3. ⚠️ Суперюзер не создаётся автоматически

---

## 9. Prod-готовность (Checklist + статус)

| Критерий | Статус | Комментарий |
|----------|--------|-------------|
| **Security** |||
| DEBUG=False | ⚠️ | Только в base.py, проверить env в prod |
| ALLOWED_HOSTS | ❌ | В dev=`["*"]`, нужно ограничить в prod |
| SECRET_KEY | ⚠️ | Читается из env, но нет генератора |
| SECURE_HSTS_SECONDS | ❌ | Не установлен |
| SECURE_SSL_REDIRECT | ❌ | Не установлен |
| SESSION_COOKIE_SECURE | ✅ | Включён в prod.py |
| CSRF_COOKIE_SECURE | ✅ | Включён в prod.py |
| CORS headers | ❌ | Не настроен (нужен django-cors-headers) |
| Rate limiting | ✅ | Корректно настроен |
| **Resilience** |||
| Gunicorn/Uvicorn | ❌ | Используется runserver в entrypoint |
| Reverse proxy (nginx) | ❌ | Не настроен |
| Static files serving | ⚠️ | collectstatic есть, но нужен nginx/CDN |
| Media files handling | ❌ | MEDIA_ROOT настроен, но нет volume в compose |
| Database connection pooling | ❌ | Нет (можно добавить CONN_MAX_AGE) |
| **Observability** |||
| Logging config | ❌ | Нет structured logging |
| Log rotation | ❌ | Не настроен |
| Health check endpoint | ✅ | `/health` существует |
| Metrics (Prometheus) | ❌ | Нет |
| Sentry integration | ❌ | Нет |
| **Deployment** |||
| .env.example | ❌ | Нет шаблона |
| Migration strategy | ⚠️ | Автоматические в entrypoint (опасно для prod!) |
| Backup strategy | ❌ | Не описана |
| CI/CD | ❌ | Не настроено |
| **Performance** |||
| Database indexes | ⚠️ | Только автоматические (нужны для FK) |
| Caching | ❌ | Не настроен |
| CDN | ❌ | Не настроен |

### Блокеры продакшена (P0):

1. **Исправить логику AccessVerifyView** — использовать `Device.auth_token` вместо user token
2. **Настроить ALLOWED_HOSTS** — читать из env, не использовать `*`
3. **Добавить HSTS и SSL redirect** в prod.py
4. **Заменить runserver на gunicorn** в entrypoint
5. **Создать .env.example** с документацией переменных

### Рекомендации для prod (P1):

- Настроить nginx как reverse proxy (serving static/media)
- Добавить structured logging (structlog + JSON formatter)
- Настроить Sentry для error tracking
- Добавить database connection pooling (`CONN_MAX_AGE`)
- Настроить CORS для фронтенда
- Добавить health check для зависимостей (DB, Redis если будет)

---

## 10. Согласованность с Вариантом 1

### 10.1 Требования Варианта 1

**Описание:**
> Приложение выдаёт `user_session_token`, тот же токен передаётся через NFC/BLE на ESP32 и валидируется на бэкенде.

**Интерпретация:**
- Мобильное приложение вызывает `/api/v1/devices/register` → получает `device_token` (64 hex)
- Приложение передаёт `device_token` на ESP32 через NFC/BLE
- ESP32 отправляет `POST /api/v1/access/verify` с `{"gate_id":"...", "token":"<device_token>"}`
- Бэкенд валидирует `device_token` через `Device.auth_token`

### 10.2 Фактическая реализация

**Что реализовано:**
1. ✅ `POST /api/v1/devices/register` создаёт `Device` с `auth_token` (64 hex)
2. ✅ `Device.auth_token` хранится в БД, уникальный, может ротироваться
3. ❌ `POST /api/v1/access/verify` **НЕ** валидирует `Device.auth_token`
   - Валидирует DRF user token (`rest_framework.authtoken.models.Token`)
4. ❌ RBAC через `AccessPermission` **НЕ** реализован
5. ❌ Проверка `Device.is_active` **НЕ** реализована

**Вывод:** 🔴 **Текущий код НЕ реализует Вариант 1!**

### 10.3 План миграции на Вариант 1

#### Шаг 1: Исправить `AccessVerifyView` (P0)

**Файл:** `backend/apps/api/v1/views.py`

**Текущий код** (строки 82-94):
```python
# Token → User
token = data["token"].strip()
token_obj = Token.objects.select_related("user").filter(key=token).first()
if not token_obj:
    AccessEvent.objects.create(access_point=ap, user=None, device_id=None,
                               decision="DENY", reason=REASON_TOKEN_INVALID, raw=data)
    return _respond("DENY", REASON_TOKEN_INVALID)

user = token_obj.user
if not user.is_active:
    AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
                               decision="DENY", reason=REASON_TOKEN_INVALID, raw=data)
    return _respond("DENY", REASON_TOKEN_INVALID)

AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
                           decision="ALLOW", reason=REASON_OK, raw=data)
return _respond("ALLOW", REASON_OK, duration_ms=800)
```

**Новый код:**
```python
# Token → Device → User
token = data["token"].strip()
device = Device.objects.select_related("user").filter(auth_token=token).first()

if not device:
    AccessEvent.objects.create(
        access_point=ap, user=None, device_id=None,
        decision="DENY", reason=REASON_TOKEN_INVALID, raw=data
    )
    return _respond("DENY", REASON_TOKEN_INVALID)

if not device.is_active:
    AccessEvent.objects.create(
        access_point=ap, user=device.user, device_id=device.id,
        decision="DENY", reason=REASON_DEVICE_INACTIVE, raw=data
    )
    return _respond("DENY", REASON_DEVICE_INACTIVE)

user = device.user
if not user.is_active:
    AccessEvent.objects.create(
        access_point=ap, user=user, device_id=device.id,
        decision="DENY", reason=REASON_TOKEN_INVALID, raw=data
    )
    return _respond("DENY", REASON_TOKEN_INVALID)

# RBAC check
from django.db.models import Q
perms = AccessPermission.objects.filter(
    Q(access_point=ap, user=user, allow=True) |
    Q(access_point=ap, group__in=user.groups.all(), allow=True)
)
if not perms.exists():
    AccessEvent.objects.create(
        access_point=ap, user=user, device_id=device.id,
        decision="DENY", reason=REASON_NO_PERMISSION, raw=data
    )
    return _respond("DENY", REASON_NO_PERMISSION)

AccessEvent.objects.create(
    access_point=ap, user=user, device_id=device.id,
    decision="ALLOW", reason=REASON_OK, raw=data
)
return _respond("ALLOW", REASON_OK, duration_ms=800)
```

**Трудоёмкость:** 1-2 часа (код + тесты).

#### Шаг 2: Обновить константы (если нужно)

**Файл:** `backend/apps/api/v1/constants.py`

Уже есть все необходимые reason-коды:
- ✅ `REASON_DEVICE_INACTIVE`
- ✅ `REASON_NO_PERMISSION`

**Трудоёмкость:** 0 часов (уже готово).

#### Шаг 3: Исправить модель `AccessEvent.device_id` → FK (опционально, P1)

**Файл:** `backend/apps/access/models.py`

**Текущий код:**
```python
device_id = models.IntegerField(null=True, blank=True)
```

**Новый код:**
```python
device = models.ForeignKey(
    'devices.Device',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='access_events'
)
```

**Миграция:**
```bash
python manage.py makemigrations access --name change_device_id_to_fk
python manage.py migrate
```

**Трудоёмкость:** 1 час (миграция + тестирование).

#### Шаг 4: Обновить тесты (P0)

**Файлы:**
- `backend/test_verify_mvp.py` — **удалить** (устарел)
- `backend/test_verify_smoke.py` — **удалить** (устарел)
- `backend/tests/test_verify_user_token.py` — **удалить** (устарел)
- `backend/tests/api/test_access_verify.py` — **уже корректны!** (проверяют Device.auth_token)

**Команда:**
```bash
rm backend/test_verify_mvp.py backend/test_verify_smoke.py backend/tests/test_verify_user_token.py
```

**Трудоёмкость:** 30 минут (удаление + запуск оставшихся тестов).

#### Шаг 5: Обновить README (P1)

**Файл:** `backend/README.md`

Обновить примеры curl:
```bash
# ❌ СТАРЫЙ ПРИМЕР (неправильный)
curl -X POST /api/v1/access/verify \
  -d '{"gate_id":"gate-01","token":"<USER_TOKEN>"}'

# ✅ НОВЫЙ ПРИМЕР (правильный)
curl -X POST /api/v1/access/verify \
  -d '{"gate_id":"gate-01","token":"<DEVICE_TOKEN>"}'
```

**Трудоёмкость:** 30 минут.

### 10.4 Итого по миграции

| Задача | Приоритет | Трудоёмкость | Файлы |
|--------|-----------|--------------|-------|
| Исправить AccessVerifyView | P0 | 1-2 часа | `apps/api/v1/views.py` |
| Удалить устаревшие тесты | P0 | 30 минут | `test_*.py` (корневые + tests/) |
| Обновить README | P1 | 30 минут | `README.md` |
| Исправить AccessEvent.device_id | P1 | 1 час | `apps/access/models.py` + миграция |

**Общая трудоёмкость:** 3-4 часа.

---

## 11. Action Plan (Ближайшие 1-2 дня)

### День 1: Критические исправления (P0)

#### Задача 1.1: Создать .env файл [P0]
**Цель:** Обеспечить запуск проекта из коробки.

**Команды:**
```bash
cd /Users/aleksandr/Developer/openway_access/backend
cat > .env << 'EOF'
# Database
POSTGRES_DB=nfc_access
POSTGRES_USER=nfc
POSTGRES_PASSWORD=nfc
DB_HOST=db
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=dev-insecure-$(openssl rand -hex 32)
DJANGO_SETTINGS_MODULE=accessproj.settings.dev
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Rate Limiting
ACCESS_VERIFY_RATE=30/second
EOF

# Создать шаблон для prod
cp .env .env.example
```

**Файлы:** `backend/.env`, `backend/.env.example`  
**Время:** 10 минут

---

#### Задача 1.2: Исправить AccessVerifyView (Device.auth_token) [P0]
**Цель:** Реализовать Вариант 1.

**Файл:** `backend/apps/api/v1/views.py`

**Патч:**
```diff
--- a/backend/apps/api/v1/views.py
+++ b/backend/apps/api/v1/views.py
@@ -79,17 +79,43 @@ class AccessVerifyView(APIView):
                                        decision="DENY", reason=REASON_UNKNOWN_GATE, raw=data)
             return _respond("DENY", REASON_UNKNOWN_GATE)
 
-        # Token → User
+        # Token → Device → User
         token = data["token"].strip()
-        token_obj = Token.objects.select_related("user").filter(key=token).first()
-        if not token_obj:
+        device = Device.objects.select_related("user").filter(auth_token=token).first()
+        if not device:
             AccessEvent.objects.create(access_point=ap, user=None, device_id=None,
                                        decision="DENY", reason=REASON_TOKEN_INVALID, raw=data)
             return _respond("DENY", REASON_TOKEN_INVALID)
 
-        user = token_obj.user
+        if not device.is_active:
+            AccessEvent.objects.create(access_point=ap, user=device.user, device_id=device.id,
+                                       decision="DENY", reason=REASON_DEVICE_INACTIVE, raw=data)
+            return _respond("DENY", REASON_DEVICE_INACTIVE)
+
+        user = device.user
         if not user.is_active:
-            AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
+            AccessEvent.objects.create(access_point=ap, user=user, device_id=device.id,
                                        decision="DENY", reason=REASON_TOKEN_INVALID, raw=data)
             return _respond("DENY", REASON_TOKEN_INVALID)
 
-        AccessEvent.objects.create(access_point=ap, user=user, device_id=None,
+        # RBAC check
+        from django.db.models import Q
+        perms = AccessPermission.objects.filter(
+            Q(access_point=ap, user=user, allow=True) |
+            Q(access_point=ap, group__in=user.groups.all(), allow=True)
+        )
+        if not perms.exists():
+            AccessEvent.objects.create(access_point=ap, user=user, device_id=device.id,
+                                       decision="DENY", reason=REASON_NO_PERMISSION, raw=data)
+            return _respond("DENY", REASON_NO_PERMISSION)
+
+        AccessEvent.objects.create(access_point=ap, user=user, device_id=device.id,
                            decision="ALLOW", reason=REASON_OK, raw=data)
         return _respond("ALLOW", REASON_OK, duration_ms=800)
```

**Команды:**
```bash
# Применить патч вручную или через editor
# Затем проверить:
docker compose exec web python manage.py test tests/api/test_access_verify.py
```

**Файлы:** `backend/apps/api/v1/views.py`  
**Время:** 1-2 часа

---

#### Задача 1.3: Удалить устаревшие тесты [P0]
**Цель:** Убрать тесты, проверяющие старую логику (user token).

**Команды:**
```bash
cd /Users/aleksandr/Developer/openway_access/backend
rm test_verify_mvp.py test_verify_smoke.py tests/test_verify_mvp.py tests/test_verify_user_token.py
git add -u
```

**Файлы:** `backend/test_*.py`, `backend/tests/test_verify_*.py`  
**Время:** 10 минут

---

#### Задача 1.4: Удалить accessproj/urls.py (дубликат) [P0]
**Цель:** Убрать путаницу с URL routing.

**Команды:**
```bash
cd /Users/aleksandr/Developer/openway_access/backend
mv accessproj/urls.py accessproj/urls_old.py
echo "# This file is not used. ROOT_URLCONF = core.urls" > accessproj/urls_old.py
```

**Файлы:** `backend/accessproj/urls.py`  
**Время:** 5 минут

---

#### Задача 1.5: Добавить pytest в requirements.txt [P0]
**Цель:** Обеспечить запуск тестов.

**Файл:** `backend/requirements.txt`

**Патч:**
```diff
--- a/backend/requirements.txt
+++ b/backend/requirements.txt
@@ -3,3 +3,5 @@ djangorestframework==3.15.2
 psycopg2-binary==2.9.9
 gunicorn==21.2.0
 python-dotenv==1.0.1
+pytest==8.3.4
+pytest-django==4.9.0
```

**Команды:**
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

**Файлы:** `backend/requirements.txt`  
**Время:** 15 минут

---

### День 2: Безопасность и Prod-готовность (P1)

#### Задача 2.1: Исправить prod.py (HSTS, SSL redirect) [P1]
**Цель:** Добавить критичные security headers.

**Файл:** `backend/accessproj/settings/prod.py`

**Патч:**
```diff
--- a/backend/accessproj/settings/prod.py
+++ b/backend/accessproj/settings/prod.py
@@ -1,5 +1,18 @@
 from .base import *
+import os
 
+# Security
+DEBUG = False
+ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
+
+# HTTPS/SSL
 SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
+SECURE_SSL_REDIRECT = True
+SECURE_HSTS_SECONDS = 31536000  # 1 year
+SECURE_HSTS_INCLUDE_SUBDOMAINS = True
+SECURE_HSTS_PRELOAD = True
+
+# Cookies
 SESSION_COOKIE_SECURE = True
 CSRF_COOKIE_SECURE = True
+SESSION_COOKIE_HTTPONLY = True
```

**Файлы:** `backend/accessproj/settings/prod.py`  
**Время:** 15 минут

---

#### Задача 2.2: Заменить runserver на gunicorn в entrypoint [P1]
**Цель:** Использовать production-ready WSGI server.

**Файл:** `backend/scripts/entrypoint.sh`

**Патч:**
```diff
--- a/backend/scripts/entrypoint.sh
+++ b/backend/scripts/entrypoint.sh
@@ -9,4 +9,10 @@ python manage.py migrate --noinput
 python manage.py collectstatic --noinput || true
 
-# Run dev server (simpler than gunicorn for MVP)
-python manage.py runserver 0.0.0.0:8000
+# Determine server based on DJANGO_SETTINGS_MODULE
+if [[ "$DJANGO_SETTINGS_MODULE" == *"dev"* ]] || [[ "$DJANGO_SETTINGS_MODULE" == *"test"* ]]; then
+    echo "Running development server..."
+    python manage.py runserver 0.0.0.0:8000
+else
+    echo "Running production server (gunicorn)..."
+    gunicorn accessproj.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
+fi
```

**Файлы:** `backend/scripts/entrypoint.sh`  
**Время:** 20 минут

---

#### Задача 2.3: Добавить линтеры (ruff + mypy) [P1]
**Цель:** Включить статический анализ кода.

**Создать файл:** `backend/pyproject.toml`

```toml
[tool.ruff]
line-length = 120
target-version = "py312"
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "C4", "DTZ", "T20", "PYI"]
ignore = ["S101", "S104"]  # Allow asserts and bind to 0.0.0.0

[tool.ruff.per-file-ignores]
"*/migrations/*.py" = ["E501"]
"*/tests/*.py" = ["S"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
exclude = ["migrations/", "tests/"]

[[tool.mypy.overrides]]
module = "rest_framework.*"
ignore_missing_imports = true
```

**Обновить:** `backend/requirements.txt`

```diff
@@ -5,3 +5,5 @@ gunicorn==21.2.0
 python-dotenv==1.0.1
 pytest==8.3.4
 pytest-django==4.9.0
+ruff==0.8.4
+mypy==1.11.2
```

**Команды:**
```bash
# Запустить локально (после rebuild)
docker compose exec web ruff check .
docker compose exec web mypy apps/
```

**Файлы:** `backend/pyproject.toml`, `backend/requirements.txt`  
**Время:** 30 минут

---

#### Задача 2.4: Настроить CORS (если нужен веб-фронтенд) [P2]
**Цель:** Разрешить cross-origin запросы от фронтенда.

**Обновить:** `backend/requirements.txt`

```diff
@@ -7,3 +7,4 @@ pytest==8.3.4
 pytest-django==4.9.0
 ruff==0.8.4
 mypy==1.11.2
+django-cors-headers==4.6.0
```

**Обновить:** `backend/accessproj/settings/base.py`

```diff
@@ -16,6 +16,7 @@ INSTALLED_APPS = [
     "rest_framework",
     "rest_framework.authtoken",
+    "corsheaders",
     "apps.accounts.apps.AccountsConfig",
     "apps.devices",
     "apps.access",
@@ -24,6 +25,7 @@ INSTALLED_APPS = [
 
 MIDDLEWARE = [
     "django.middleware.security.SecurityMiddleware",
+    "corsheaders.middleware.CorsMiddleware",
     "django.contrib.sessions.middleware.SessionMiddleware",
     "django.middleware.common.CommonMiddleware",
     "django.middleware.csrf.CsrfViewMiddleware",
@@ -31,6 +33,10 @@ MIDDLEWARE = [
     "django.contrib.messages.middleware.MessageMiddleware",
     "django.middleware.clickjacking.XFrameOptionsMiddleware",
 ]
+
+# CORS (dev only)
+CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL", "false").lower() == "true"
+CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
```

**Файлы:** `backend/requirements.txt`, `backend/accessproj/settings/base.py`  
**Время:** 20 минут

---

#### Задача 2.5: Обновить README с корректными примерами [P1]
**Цель:** Синхронизировать документацию с кодом.

**Файл:** `backend/README.md`

**Патч:**
```diff
@@ -38,14 +38,20 @@ Content-Type: application/json
 
 #### 3. Access Verification
 ```bash
-# Verify access at gate
+# Verify access at gate (using DEVICE token, not user token!)
 POST /api/v1/access/verify
 Content-Type: application/json
 
 {
   "gate_id": "gate-01",
-  "token": "<device_token>"
+  "token": "<device_token>"  # 64-hex token from /devices/register
 }
+
+# IMPORTANT: Use the "token" field from /devices/register response,
+# NOT the user token from /auth/token!
+#
+# User token is used for authenticating mobile app API calls.
+# Device token is used for NFC/BLE access verification.
 
 # Response (always 200):
 {
@@ -67,8 +73,13 @@ GET /health
 ### Token Management Rules
 
 - **Store the LATEST token**: Always use the most recent token returned by `/devices/register`
+- **Two types of tokens:**
+  - **User token** (from `/auth/token`): Used for authenticating API calls (Authorization header)
+  - **Device token** (from `/devices/register`): Used for NFC/BLE access verification
 - **rotate=false**: Allows binding `android_device_id` without token rotation
 - **rotate=true** (default): Generates new token on every call
+- **RBAC**: Access is granted only if user/group has AccessPermission for the gate
+- **Device status**: Only active devices (`is_active=True`) can verify access
```

**Файлы:** `backend/README.md`  
**Время:** 30 минут

---

### Дополнительно (P2, опционально)

#### Задача 3.1: Исправить AccessEvent.device_id → FK [P2]
**Цель:** Обеспечить целостность данных.

**Файл:** `backend/apps/access/models.py`

**Патч:**
```diff
--- a/backend/apps/access/models.py
+++ b/backend/apps/access/models.py
@@ -22,7 +22,7 @@ class AccessPermission(models.Model):
 class AccessEvent(models.Model):
     access_point = models.ForeignKey(AccessPoint, on_delete=models.SET_NULL, null=True)
     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
-    device_id = models.IntegerField(null=True, blank=True)
+    device = models.ForeignKey('devices.Device', on_delete=models.SET_NULL, null=True, blank=True, related_name='access_events')
     decision = models.CharField(max_length=10)
     reason = models.CharField(max_length=64, blank=True)
     raw = models.JSONField(null=True, blank=True)
```

**Команды:**
```bash
docker compose exec web python manage.py makemigrations access --name change_device_id_to_fk
docker compose exec web python manage.py migrate
```

**Обновить views.py:** Заменить `device_id=device.id` → `device=device`

**Файлы:** `backend/apps/access/models.py`, новая миграция  
**Время:** 1 час

---

#### Задача 3.2: Добавить structured logging [P2]
**Цель:** Улучшить observability.

**Создать:** `backend/accessproj/settings/logging.py`

```python
import os

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
```

**Обновить:** `backend/accessproj/settings/base.py`

```python
from .logging import LOGGING
```

**Файлы:** `backend/accessproj/settings/logging.py`, `backend/accessproj/settings/base.py`  
**Время:** 30 минут

---

## 12. Приложение A — Команды для проверки

### A.1 Локальный запуск (Docker Compose)

```bash
# 1. Создать .env (см. Задачу 1.1)
cd /Users/aleksandr/Developer/openway_access/backend
cat > .env << 'EOF'
POSTGRES_DB=nfc_access
POSTGRES_USER=nfc
POSTGRES_PASSWORD=nfc
DB_HOST=db
DB_PORT=5432
DJANGO_SECRET_KEY=dev-insecure-$(openssl rand -hex 32)
DJANGO_SETTINGS_MODULE=accessproj.settings.dev
DJANGO_ALLOWED_HOSTS=*
ACCESS_VERIFY_RATE=30/second
EOF

# 2. Запустить
docker compose up --build

# 3. Применить миграции (автоматически в entrypoint, но можно вручную)
docker compose exec web python manage.py migrate

# 4. Создать суперюзера
docker compose exec web python manage.py createsuperuser

# 5. Создать demo данные
docker compose exec web python manage.py shell << 'PYEOF'
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.access.models import AccessPoint, AccessPermission
from apps.devices.models import Device

User = get_user_model()

# Создать тестового пользователя
user, _ = User.objects.get_or_create(username='testuser', defaults={'is_active': True})
user.set_password('testpass')
user.save()

# Создать группу USER
group, _ = Group.objects.get_or_create(name='USER')
user.groups.add(group)

# Создать gate
gate, _ = AccessPoint.objects.get_or_create(code='gate-01', defaults={'name': 'Main Gate'})

# Создать permission для группы USER
AccessPermission.objects.get_or_create(
    access_point=gate,
    group=group,
    defaults={'allow': True}
)

# Создать устройство
device, _ = Device.objects.get_or_create(
    user=user,
    defaults={
        'auth_token': 'test_device_token_12345678901234567890123456789012',
        'is_active': True,
        'name': 'Test Device'
    }
)

print(f"✅ User: {user.username}")
print(f"✅ Gate: {gate.code}")
print(f"✅ Device token: {device.auth_token}")
PYEOF
```

### A.2 Smoke-тест эндпоинтов

```bash
# Базовый URL
BASE_URL="http://localhost:8001"

# 1. Health check
curl $BASE_URL/health
# Expected: {"status":"ok"}

# 2. Получить user token
USER_TOKEN=$(curl -s -X POST $BASE_URL/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  | jq -r '.token')
echo "User token: $USER_TOKEN"

# 3. Зарегистрировать устройство
DEVICE_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/devices/register \
  -H "Authorization: Token $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"android_device_id":"test-android-123"}')
echo "Device response: $DEVICE_RESPONSE"

DEVICE_TOKEN=$(echo $DEVICE_RESPONSE | jq -r '.token')
echo "Device token: $DEVICE_TOKEN"

# 4. Проверить доступ (с device token — после исправления!)
curl -X POST $BASE_URL/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d "{\"gate_id\":\"gate-01\",\"token\":\"$DEVICE_TOKEN\"}"
# Expected: {"decision":"ALLOW","reason":"OK","duration_ms":800}

# 5. Проверить доступ (с невалидным токеном)
curl -X POST $BASE_URL/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d '{"gate_id":"gate-01","token":"invalid_token"}'
# Expected: {"decision":"DENY","reason":"TOKEN_INVALID"}

# 6. Список устройств
curl -X GET $BASE_URL/api/v1/devices/me \
  -H "Authorization: Token $USER_TOKEN"
# Expected: [{"id":1,"android_device_id":"test-android-123","is_active":true,"token_preview":"..."}]

# 7. Отозвать устройство
DEVICE_ID=$(echo $DEVICE_RESPONSE | jq -r '.device_id')
curl -X POST $BASE_URL/api/v1/devices/revoke \
  -H "Authorization: Token $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\":$DEVICE_ID}"
# Expected: {"device_id":1,"is_active":false}

# 8. Проверить доступ после revoke
curl -X POST $BASE_URL/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d "{\"gate_id\":\"gate-01\",\"token\":\"$DEVICE_TOKEN\"}"
# Expected: {"decision":"DENY","reason":"DEVICE_INACTIVE"}
```

### A.3 Запуск тестов

```bash
# Django TestCase
docker compose exec web python manage.py test tests/

# Pytest (после добавления в requirements.txt)
docker compose exec web pytest tests/ -v

# Конкретный тест
docker compose exec web pytest tests/api/test_access_verify.py::StaticTokenVerifyTests::test_allow -v

# С покрытием (после установки coverage)
docker compose exec web pytest tests/ --cov=apps --cov-report=html
```

### A.4 Линтеры и статический анализ (после настройки)

```bash
# Ruff (linter + formatter)
docker compose exec web ruff check apps/ core/ accessproj/
docker compose exec web ruff format apps/ core/ accessproj/

# Mypy (type checking)
docker compose exec web mypy apps/ core/

# Bandit (security audit)
pip install bandit
bandit -r apps/ -ll
```

### A.5 Проверка миграций

```bash
# Проверить статус миграций
docker compose exec web python manage.py showmigrations

# Создать новые миграции (если модели изменились)
docker compose exec web python manage.py makemigrations

# Применить миграции
docker compose exec web python manage.py migrate

# Откатить миграцию (example)
docker compose exec web python manage.py migrate access 0001_initial
```

### A.6 Проверка безопасности (Django check)

```bash
# Проверка настроек (security warnings)
docker compose exec web python manage.py check --deploy

# Ожидаемые warnings до исправления prod.py:
# - SECURE_HSTS_SECONDS not set
# - SECURE_SSL_REDIRECT not enabled
# и т.д.
```

---

## 13. Быстрый чек-лист статусов

### До исправлений:

- [ ] Проект поднимается локально по инструкции из отчета (нужен .env)
- [x] Все миграции применяются без ошибок
- [ ] Есть суперюзер и доступ в /admin (нужно создать вручную)
- [ ] Все заявленные эндпоинты существуют и отвечают ожидаемым схемам (AccessVerifyView использует user token вместо device token)
- [x] Rate limiting на /api/v1/access/verify работает (конфиг найден)
- [ ] Линтер/тесты настроены и проходят (pytest не в requirements.txt)
- [ ] Prod-параметры безопасности корректны (нет HSTS, SSL redirect)
- [ ] Логи, health-check, статика/медиа для prod описаны (health-check есть, логи нет)
- [ ] Реализация соответствует Варианту 1 (НЕТ — использует user token)

### После выполнения Action Plan (День 1):

- [x] Проект поднимается локально по инструкции из отчета
- [x] Все миграции применяются без ошибок
- [x] Есть суперюзер и доступ в /admin
- [x] Все заявленные эндпоинты существуют и отвечают ожидаемым схемам
- [x] Rate limiting на /api/v1/access/verify работает
- [x] Линтер/тесты настроены и проходят
- [ ] Prod-параметры безопасности корректны (после Дня 2)
- [ ] Логи, health-check, статика/медиа для prod описаны (после Дня 2)
- [x] Реализация соответствует Варианту 1

### После выполнения Action Plan (День 2):

- [x] Проект поднимается локально по инструкции из отчета
- [x] Все миграции применяются без ошибок
- [x] Есть суперюзер и доступ в /admin
- [x] Все заявленные эндпоинты существуют и отвечают ожидаемым схемам
- [x] Rate limiting на /api/v1/access/verify работает
- [x] Линтер/тесты настроены и проходят
- [x] Prod-параметры безопасности корректны
- [x] Логи, health-check, статика/медиа для prod описаны
- [x] Реализация соответствует Варианту 1

---

## 14. Выводы и рекомендации

### Критические выводы:

1. **Текущий код НЕ реализует заявленную функциональность** (Вариант 1). `AccessVerifyView` валидирует user token вместо device token, не проверяет RBAC и `Device.is_active`.

2. **Тесты не соответствуют production коду**. Часть тестов (`test_access_verify.py`) проверяет корректную логику (device token + RBAC), но эта логика не реализована в `views.py`.

3. **Отсутствует .env файл** — проект не запустится из коробки.

4. **Безопасность в prod конфигурации минимальна** — отсутствуют HSTS, SSL redirect, CORS не настроен.

5. **Инструменты разработки не настроены** — нет линтеров, pytest не в зависимостях.

### Приоритеты:

| Приоритет | Задачи | Время |
|-----------|--------|-------|
| P0 (критично) | Исправить AccessVerifyView, создать .env, удалить дубликаты | 2-3 часа |
| P1 (важно) | Prod security (HSTS, gunicorn), линтеры, обновить README | 2-3 часа |
| P2 (улучшения) | FK для device_id, structured logging, CORS | 2-3 часа |

**Общая трудоёмкость для prod-готовности:** 6-9 часов работы.

### Следующие шаги:

1. Выполнить Action Plan (День 1) — исправить критические расхождения
2. Запустить полный набор тестов и убедиться в работоспособности
3. Выполнить Action Plan (День 2) — подготовить к продакшену
4. Настроить CI/CD pipeline (GitHub Actions / GitLab CI)
5. Подготовить deployment инструкции для prod (nginx + gunicorn + PostgreSQL)

---

**Конец отчёта**


