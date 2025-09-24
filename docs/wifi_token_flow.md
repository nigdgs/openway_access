# Wi-Fi Token Flow MVP

## Последовательная диаграмма
```mermaid
sequenceDiagram
    participant AndroidApp
    participant Backend
    participant Postgres as PostgreSQL
    participant ESP32

    AndroidApp->>Backend: POST /api/v1/auth/token (username, password)
    Backend-->>AndroidApp: 200 {token}

    AndroidApp->>Backend: POST /api/v1/devices/register (rotate?, android_device_id)
    Backend-->>AndroidApp: 200 {device_id, token, qr_payload}
    Backend->>Postgres: upsert Device, AccessEvent

    AndroidApp->>ESP32: HTTP POST /wifi/token {gate_id, device_token, nonce, ttl}
    ESP32->>ESP32: Cache token (ttl, nonce, signature)

    activate ESP32
    ESP32->>Backend: POST /api/v1/access/verify {gate_id, token, nonce}
    Backend->>Postgres: look up Device, Access permissions
    Backend-->>ESP32: 200 {decision, reason, duration_ms}
    ESP32-->>AndroidApp: optional ACK /wifi/token/ack {decision}
    deactivate ESP32

    ESP32->>Backend: POST /api/v1/access/events (future) {gate_id, decision, rssi, firmware}
```

## Anti-replay и логирование
- Использовать одноразовый `nonce` и короткий TTL (5–10 сек) для передачи токена через Wi-Fi.
- ESP32 обязан инвалидировать токен после получения `ALLOW/DENY` или по истечении TTL.
- Backend при проверке токена сохраняет `nonce` в `AccessEvent.raw` и отклоняет повторные попытки (потребуется отдельный сторедж или Redis).
- Расширить `AccessEvent` полями `transport`, `firmware_version`, `rssi` для наблюдаемости.

## Чек-лист интеграции — Android
- [ ] Реализовать UI для фонового Wi-Fi обмена с ESP32 (HTTP POST /wifi/token).
- [ ] Хранить `Authorization: Token <api_token>` и ротировать через `/devices/register` при каждом логине.
- [ ] Генерировать `nonce` (UUIDv4) и отправлять TTL, gate_id, device_token.
- [ ] Включить журналирование: success/fail, gate_id, decision.
- [ ] Обрабатывать `RATE_LIMIT` и повторять запрос через backoff.

## Чек-лист интеграции — ESP32
- [ ] HTTP endpoint `/wifi/token` (POST) с полями `gate_id`, `token`, `nonce`, `ttl`.
- [ ] Хранить активный токен в RAM, инвалидировать по TTL или после запроса к backend.
- [ ] Конфигурируемые параметры: backend host/port, verify timeout, retry strategy.
- [ ] Реализовать `POST /api/v1/access/verify` c заголовком `X-Request-ID` и логами `decision/reason`.
- [ ] Добавить диод/реле управления по `decision` и отдавать ACK в Android при успехе/ошибке.
- [ ] При недоступности backend — локальный fail-safe (например, deny + сигнализация).

## Минимальные доработки backend для Wi-Fi MVP
- [ ] Расширить `VerifyRequestSerializer` полями `nonce`, `ttl_ms`, `transport="wifi"`.
- [ ] Проверять одноразовость nonce (Redis или таблица `AccessNonce`).
- [ ] Добавить throttle по ESP32 (`drf` scope `access_verify_wifi`).
- [ ] Логировать `request_id`, `gate_id`, `device_id`, `transport` в structured logs.
- [ ] Подготовить `/api/v1/access/verify/wifi` (опционально) с обязательными контрольными полями.
