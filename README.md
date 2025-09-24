# OpenWay Access — Backend & Platform

Мобильная пропускная система: Android-приложение, backend на Django/DRF, база PostgreSQL и прошивка ESP32. Текущая версия использует статический device token; планируется миграция на Wi-Fi поток выдачи токена.

## Быстрый старт

### 1. Docker Compose (рекомендовано)
1. Скопируйте `.env.example` → `.env` и при необходимости отредактируйте переменные.
2. Запустите сервисы:
   ```bash
   make up
   ```
3. Примените миграции и создайте демо-данные (опционально):
   ```bash
   docker compose -f backend/compose.yml --env-file .env exec web python manage.py migrate --noinput
   docker compose -f backend/compose.yml --env-file .env exec web python manage.py createsuperuser
   ```
4. Backend доступен на `http://localhost:8001` (web → 8000 внутри контейнера).

### 2. Локально (без Docker)
1. Создайте `.venv` и установите зависимости:
   ```bash
   make venv
   make deps
   cp .env.example .env
   ```
2. Запустите Postgres (локально или через docker `db` сервис) и обновите `DB_HOST` при необходимости.
3. Примените миграции и стартуйте сервер:
   ```bash
   make migrate DJANGO_SETTINGS=accessproj.settings.dev
   make runserver
   ```

## Тесты и качество
- Юнит-тесты: `make test` (использует sqlite + coverage, результат в `coverage.xml`).
- Линты: `make lint` (ruff, black, isort, mypy, bandit).
- Форматирование: `make fmt`.
- Нагрузочный сценарий verify: `make loadtest` (требуется установленный `k6`).
- CI конвейер: `.github/workflows/ci.yml` (lint → test → docker build).

> ⚠️ В текущем окружении зависимости PyPI не устанавливаются (ограниченный индекс). Перед запуском тестов и линтов необходимо установить пакеты из `backend/requirements.txt` и `backend/requirements-dev.txt` в среде с доступом в интернет.

## Переменные окружения
| Переменная | Где используется | Значение по умолчанию | Обязательна |
|------------|------------------|-----------------------|-------------|
| `DJANGO_SECRET_KEY` | `accessproj/settings/base.py` | `dev-secret` | ✅ (прод) |
| `DJANGO_SETTINGS_MODULE` | manage.py, wsgi/asgi, Makefile | `accessproj.settings.dev` | ♻️ |
| `DJANGO_ALLOWED_HOSTS` | `accessproj/settings/base.py` | `*` | ✅ (прод) |
| `POSTGRES_DB` | `accessproj/settings/base.py`, compose | `nfc_access` | ✅ |
| `POSTGRES_USER` | `accessproj/settings/base.py`, compose | `nfc` | ✅ |
| `POSTGRES_PASSWORD` | `accessproj/settings/base.py`, compose | `nfc` | ✅ |
| `DB_HOST` | `accessproj/settings/base.py`, wait-for-db.sh | `db` | ✅ |
| `DB_PORT` | `accessproj/settings/base.py` | `5432` | ♻️ |
| `ACCESS_VERIFY_RATE` | `REST_FRAMEWORK[DEFAULT_THROTTLE_RATES]` | `30/second` | ♻️ |
| `LOG_LEVEL` | (предлагается) | `INFO` | ☐ |
| `REQUEST_ID_HEADER` | (предлагается) | `X-Request-ID` | ☐ |

Актуальный шаблон: `.env.example` в корне. Файл `backend/.env.example` устарел — используйте новый шаблон.

## API и документация
- OpenAPI спек: `docs/openapi.yaml` (совместна с Android/ESP32).
- Wi-Fi поток выдачи токена: `docs/wifi_token_flow.md` (sequence-diagram + чек-листы).
- Runbook для on-call: `docs/RUNBOOK.md`.
- Полный аудит и рекомендации: `REPORT.md`.

Основные эндпоинты (см. doc/openapi):
- `POST /api/v1/auth/token` — получение DRF токена пользователя.
- `POST /api/v1/devices/register` — регистрация/ротация device token.
- `GET /api/v1/devices/me` — список активных устройств.
- `POST /api/v1/devices/revoke` — деактивация.
- `POST /api/v1/access/verify` — проверка контроллером (возвращает ALLOW/DENY, не использует HTTP 4xx/5xx).

## Wi-Fi быстрый старт (ESP32 → backend)
1) Поднимите backend: `docker compose -f backend/compose.yml up -d` и примените миграции.
2) Убедитесь, что в `.env` задано:
   ```
   ACCESS_VERIFY_RATE=30/second
   ACCESS_VERIFY_WIFI_RATE=30/second
   ```
3) Тест напрямую:
   ```bash
   http POST http://<backend-ip>:8001/api/v1/access/verify gate_id=gate-01 token=DEADBEEF
   ```
4) Тест через ESP32:
   ```bash
   curl -X POST http://<ESP_IP>/enter -H "Content-Type: application/json" \
     -d '{"token":"DEADBEEF1234","gate_id":"gate-01"}'
   ```
**Примечание:** поле `duration_ms` в ответе совместимое; фактическое время обработки см. в `AccessEvent.raw.processing_ms`.

## Wi-Fi MVP (кратко)
1. Android получает user token (`/auth/token`) → device token (`/devices/register`).
2. Передает `token + gate_id + nonce + ttl` на ESP32 (HTTP по Wi-Fi).
3. ESP32 хранит токен до запроса и выполняет `/api/v1/access/verify`.
4. Backend логирует AccessEvent и отвечает `ALLOW/DENY`.
5. Последовательность и чек-листы — в `docs/wifi_token_flow.md`.

## Дополнительные каталоги
- `android/OpenWay` — Android приложение (Kotlin, Gradle).
- `firmware/src/main.cpp` — прошивка ESP32 (PlatformIO).
- `infra/docker-compose.yml` — альтернативный compose для локальной инфраструктуры.

## Полезные команды
```bash
# миграции в docker
make up
make migrate DJANGO_SETTINGS=accessproj.settings.dev

# запуск smoke verify
http POST :8001/api/v1/access/verify gate_id=gate-01 token=dummy

# просмотреть последние события
python backend/manage.py shell --settings=accessproj.settings.dev \
  -c "from apps.access.models import AccessEvent; print(list(AccessEvent.objects.order_by('-created_at')[:5]))"
```

## Ссылки
- [REPORT.md](REPORT.md) — аудит и план миграции.
- [docs/openapi.yaml](docs/openapi.yaml) — схемы API.
- [docs/wifi_token_flow.md](docs/wifi_token_flow.md) — Wi-Fi поток.
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — каталог действий on-call.
- [perf/k6_verify.js](perf/k6_verify.js) — сценарий нагрузочного теста.
