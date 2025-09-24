# Issue Log

1. [P0] Жестко заданный SECRET_KEY и ALLOWED_HOSTS по умолчанию приводят к небезопасному прод-режиму — исправить в `backend/accessproj/settings/base.py:5` и `backend/accessproj/settings/base.py:7`, делая переменные обязательными в prod и добавляя в CI проверку.
2. [P0] `/api/v1/access/verify` не защищён от повторного воспроизведения токена (нет nonce/ttl) — доработать `backend/apps/api/v1/serializers.py:4` и `backend/apps/api/v1/views.py:71`, добавив nonce, TTL и хранилище одноразовых записей.
3. [P0] Device token хранится и передаётся в открытом виде (без подписи, нет истечения) — пересмотреть контракт в `backend/apps/api/v1/views.py:149` и на клиенте; добавить короткоживущие токены или HMAC.
4. [P1] Уникальность `AccessPermission` с `unique_together` не работает для `NULL` значений (`backend/apps/access/models.py:20`) — заменить на `UniqueConstraint` с условиями (отдельно для user и group).
5. [P1] `AccessEvent.device_id` (`backend/apps/access/models.py:25`) хранится как число без FK → нет целостности и каскадных удалений; мигрировать на ForeignKey.
6. [P1] Нет выделенного throttle/лимита для Wi-Fi контроллеров (`backend/apps/api/v1/views.py:57`) — добавить отдельную scope `access_verify_wifi` и конфиг через ENV.
7. [P1] Отсутствуют структурированные логи и request-id (затрудняет аудит) — внедрить JSON-логирование и middleware (`accessproj/settings/base.py`, `core/`).
8. [P1] Нет CORS/CSRF политики для мобильного клиента (`accessproj/settings/base.py`); требуется определить допустимые origin и запретить '*' в prod.
9. [P1] Нет health-check для БД/фоновых зависимостей кроме `/health` (только статика) — расширить `core/views.py:4` и добавить прометей-метрики/статус Postgres.
10. [P1] README/compose не описывает как запускать PostgreSQL для локального девелопмента без Docker (`infra/docker-compose.yml`) — обновить документацию и скрипты данных.
