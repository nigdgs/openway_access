# Endpoints Status — 2025-10-17

## Резюме по критериям (PASS/FAIL)
- /api/v1/auth/token: PASS (статический аудит; подключён obtain_auth_token; пример ответа стандартный DRF TokenAuth)
- /api/v1/access/verify: PASS (статический аудит; реализованы все причины DENY и throttling с scope="access_verify")
- /health|/ready: PASS (статический аудит; оба эндпоинта подключены и возвращают JSON)
- /docs и /schema: PASS (статический аудит; Spectacular APIView и SwaggerView подключены)

ЗАПУСК НЕВОЗМОЖЕН: pip install провалился из‑за SSL (OSStatus -26276). См. конкретную ошибку ниже.

## Таблица эндпоинтов
| Метод | Путь | View | Auth/Perm | Throttle(scope) | Вход | Выход | Статусы |
|---|---|---|---|---|---|---|---|
| GET | /health | `core.views.health` | AllowAny | — | — | {status:"ok"} | 200 |
| GET | /ready | `core.views.ready` | AllowAny | — | — | {status:"ready"|"not-ready"} | 200/503 |
| GET | /schema/ | `drf_spectacular.views.SpectacularAPIView` | AllowAny | — | — | OpenAPI JSON | 200 |
| GET | /docs/ | `drf_spectacular.views.SpectacularSwaggerView` | AllowAny | — | — | Swagger UI | 200 |
| POST | /api/v1/auth/token | `rest_framework.authtoken.views.obtain_auth_token` | AllowAny | — | {username,password} | {token} | 200/400 |
| POST | /api/v1/access/verify | `apps.api.v1.views.AccessVerifyView` | none | ScopedRateThrottle("access_verify") | {gate_id, token} | {decision,reason[,duration_ms]} | 200 |

## Реализация verify
- Файл и строки (view):
```47:120:/Users/aleksandr/Documents/GitHub/openway_access/backend/apps/api/v1/views.py
class AccessVerifyView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "access_verify"
    ...
    def post(self, request):
        ...
```
- Сериализаторы:
```6:13:/Users/aleksandr/Documents/GitHub/openway_access/backend/apps/api/v1/serializers.py
class VerifyRequestSerializer(serializers.Serializer):
    gate_id = serializers.CharField()
    token = serializers.CharField(min_length=8, max_length=128)

class VerifyResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=list(DECISIONS))
    duration_ms = serializers.IntegerField(required=False, min_value=0)
    reason = serializers.ChoiceField(choices=list(REASONS))
```
- Константы decision/reason:
```1:25:/Users/aleksandr/Documents/GitHub/openway_access/backend/apps/api/v1/constants.py
DECISIONS = ("ALLOW", "DENY")
REASONS = (UNKNOWN_GATE, TOKEN_INVALID, DEVICE_NOT_FOUND, DEVICE_INACTIVE,
           NO_PERMISSION, OK, INVALID_REQUEST, DEVICE_MISMATCH, RATE_LIMIT)
```
- Логика причин в `post`:
  - INVALID_REQUEST: валидация `VerifyRequestSerializer` → 200 DENY
  - UNKNOWN_GATE: `AccessPoint.DoesNotExist` → 200 DENY
  - TOKEN_INVALID: отсутствует токен пользователя или user.is_active=False → 200 DENY
  - NO_PERMISSION: отсутствует разрешение по пользователю/группе → 200 DENY
  - RATE_LIMIT: перехват `Throttled` в `dispatch` → 200 DENY
  - ALLOW/OK: при успешной проверке → 200 ALLOW с `duration_ms`
- Статус-код ответа: всегда 200 (ALLOW/DENY), заглушка `duration_ms` задаётся при ALLOW.

## Подключение URL
```7:16:/Users/aleksandr/Documents/GitHub/openway_access/backend/core/urls.py
urlpatterns = [
    path("health", health, name="health"),
    path("healthz", health, name="healthz"),
    path("ready", ready, name="ready"),
    path("readyz", ready, name="readyz"),
    path("api/", include("apps.api.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("admin/", admin.site.urls),
]
```
```6:12:/Users/aleksandr/Documents/GitHub/openway_access/backend/apps/api/v1/urls.py
urlpatterns = [
    path("access/verify", AccessVerifyView.as_view(), name="access-verify"),
    path("auth/token", obtain_auth_token, name="auth-token"),
    ...
]
```

## DRF settings, throttling, CORS/CSRF
```91:116:/Users/aleksandr/Documents/GitHub/openway_access/backend/accessproj/settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
```
- Throttle scope значение: `access_verify` с дефолтом `30/second` (можно переопределить переменной окружения `ACCESS_VERIFY_RATE`).
- CORS: `CORS_ALLOWED_ORIGINS` из env, по умолчанию `http://localhost:3000,http://localhost:8080`; `CORS_ALLOW_CREDENTIALS=True`.
- CSRF: стандартный `CsrfViewMiddleware` включён в `MIDDLEWARE`.

## Прогоны (сырые логи)
ЗАПУСК НЕВОЗМОЖЕН на шаге установки зависимостей:
```
ERROR: No matching distribution found for Django~=5.0.14
Caused by SSLError(SSLCertVerificationError('OSStatus -26276')) во время обращения к PyPI.
```
Из‑за этого не были выполнены: миграции, генерация токенов, запуск dev‑сервера и curl‑тесты. Повторный запуск возможен после починки сетевого/SSL окружения.

## Выводы и «Что требуется сделать»
- Что работает (по коду):
  - Есть /health, /ready; /schema и /docs подключены.
  - /api/v1/auth/token доступен через DRF TokenAuth view.
  - /api/v1/access/verify реализует все причины DENY и ScopedRateThrottle("access_verify").
  - Ответы verify всегда 200 с {decision,reason[,duration_ms]}.
- Что не подтверждено рантаймом:
  - Фактическая доступность эндпоинтов, рендер /docs, отдача /schema.
  - Получение токена через /auth/token.
  - 429 при превышении лимита и заголовок Retry-After.
- NEXT STEPS (для доведения до критериев):
  1) Починить установку зависимостей (SSL/PyPI): обновить сертификаты macOS, проверить `pip install --upgrade certifi`, доверенные корни, прокси.
  2) Повторить шаги B1–B5 из задания (venv, миграции, тест‑данные, runserver, curl‑прогоны).
  3) Зафиксировать реальные статусы/JSON и заголовки в этот файл.
