# MVP Access Control — Backend (Django + DRF + Postgres)

A minimal, production-leaning MVP for NFC-based access control with **static device tokens** (for fast integration/testing).  
Stack: **Django/DRF**, **PostgreSQL**, **Docker Compose**.

## TL;DR Quickstart

```bash
# 1) Start services
docker compose -f backend/compose.yml up -d

# 2) Apply migrations
docker compose -f backend/compose.yml exec -T web python manage.py migrate --noinput

# 3) Reset demo data (purge logs/users/devices; create fresh admin+demo, gate, permissions, device token)
./reset_demo.sh

# 4) Open Admin (login: admin / StrongPass_123)
http://localhost:8001/admin/
```

## API Endpoints (v1)

### Auth — obtain user API token
```css
POST /api/v1/auth/token
Body: {"username":"<user>","password":"<pass>"}
Response: {"token":"<api_token>"}
```

### Devices — register/rotate device token (requires Authorization: Token <api_token>)
```swift
POST /api/v1/devices/register
Body: {"android_device_id":"android-xyz", "rotate":false} // both optional
Resp: {"device_id":123,"token":"<device_token>","android_device_id":"android-xyz","qr_payload":"acc://token?value=..."}
```

List & revoke:
```bash
GET  /api/v1/devices/me
POST /api/v1/devices/revoke   // body: {"device_id":123} or {"android_device_id":"android-xyz"}
```

### Access Verify — controller to server
```css
POST /api/v1/access/verify
Body: {"gate_id":"gate-01","token":"<device_token>"}
200 OK:
  - ALLOW: {"decision":"ALLOW","reason":"OK","duration_ms":800}
  - DENY:  {"decision":"DENY","reason":"TOKEN_INVALID|NO_PERMISSION|DEVICE_INACTIVE|UNKNOWN_GATE|INVALID_REQUEST|RATE_LIMIT"}
```

Rate limiting: `ACCESS_VERIFY_RATE` (env) limits `/access/verify` requests (default 30/second). On throttle returns 200 DENY/RATE_LIMIT.

## Handy Scripts

### verify.sh — quick ALLOW/DENY check:
```bash
# direct
TOKEN=<device_token> ./verify.sh
# by device
DEVICE_ID=<id> ./verify.sh
# by user (latest active device)
USER_ID=<id> ./verify.sh
```

### e2e_static_token_check.sh — full end-to-end checks (allow/deny variants, events summary, tests).

### reset_demo.sh — purge+seed clean demo (see below).

## Reset Demo (clean admin, fresh users, fresh data)
```bash
./reset_demo.sh
# creates:
#   - superuser: admin / StrongPass_123
#   - user:      demo  / StrongPass_123
#   - gate:      gate-01  (AccessPoint)
#   - group:     USER  (allow at gate-01)
#   - device:    demo's active device with a fresh token (printed)
```

Use printed token with verify.sh:
```bash
TOKEN=<copied_token> ./verify.sh
```

## Troubleshooting

**404 on /api/v1/access/verify** — ensure core.urls has:
```python
from apps.api.v1.views import AccessVerifyView
urlpatterns += [path("api/v1/access/verify", AccessVerifyView.as_view(), name="access-verify")]
```
Restart web: `docker compose -f backend/compose.yml restart web`

**DisallowedHost** — add localhost in dev ALLOWED_HOSTS or .env.

**Settings not configured** — always run via manage.py or export DJANGO_SETTINGS_MODULE.

**Can't reach port** — verify.sh auto-detects 8001→8000. Or check ports: in backend/compose.yml.

## Dev Notes

Static token is for MVP/testing. For higher security consider HMAC challenge-response or device key signatures (Android Keystore).

**DB inspection (optional):**
```bash
docker compose -f backend/compose.yml exec -T web python manage.py dbshell <<'SQL'
\dt
\d+ devices_device
\d+ access_accesspoint
\d+ access_accesspermission
\d+ access_accessevent
SQL
```
