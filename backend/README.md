# Access Control MVP Backend

## Quick Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

3. **Create superuser:**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## Android Integration Quickstart

### Endpoints and Formats

#### 1. Authentication
```bash
# Get user token
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=<user>&password=<pass>

# Response: {"token": "abc123..."}
```

#### 2. Device Registration
```bash
# Register/rotate device token
POST /api/v1/devices/register
Authorization: Token <user_token>
Content-Type: application/json

{
  "rotate": true,  // optional, defaults to true
  "android_device_id": "emu-5554"  // optional
}

# Response:
{
  "device_id": 123,
  "token": "64-hex-character-token",
  "qr_payload": "64-hex-character-token",
  "android_device_id": "emu-5554"
}
```

#### 3. Access Verification

**⚠️ IMPORTANT: Uses `user_session_token` (DRF TokenAuth), NOT device token!**

```bash
# Verify access at gate using user_session_token
curl -X POST http://localhost:8001/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d '{
    "gate_id": "gate-01",
    "token": "<USER_SESSION_TOKEN_FROM_/api/v1/auth/token>"
  }'

# Response (always 200):
{
  "decision": "ALLOW",  // or "DENY"
  "reason": "OK",       // or error reason code
  "duration_ms": 800    // optional, only present on ALLOW
}
```

**RBAC (Role-Based Access Control):**
- Access is granted if there exists an `AccessPermission` for:
  - The **user** directly: `AccessPermission(user=<user>, access_point=<gate>, allow=True)`
  - OR any of the **user's groups**: `AccessPermission(group__in=<user.groups>, access_point=<gate>, allow=True)`

**Possible reasons:**
- `OK` — Access granted
- `TOKEN_INVALID` — Invalid or inactive user token
- `UNKNOWN_GATE` — Gate ID does not exist
- `NO_PERMISSION` — User/groups lack permission for this gate
- `INVALID_REQUEST` — Malformed request
- `RATE_LIMIT` — Too many requests

#### 4. Health Check
```bash
# Check service health
GET /health

# Response: {"status": "ok"}
```

### Token Management Rules

**User Session Tokens (for `/api/v1/access/verify`):**
- Obtained from `/api/v1/auth/token` after login
- Used directly for access verification at gates
- Same token is shared with ESP32 via NFC/BLE
- Standard DRF TokenAuthentication (40 hex characters)

**Device Tokens (for `/devices/register`, optional):**
- **Store the LATEST token**: Always use the most recent token returned by `/devices/register`
- **rotate=false**: Allows binding `android_device_id` without token rotation
- **rotate=true** (default): Generates new token on every call
- **Token length**: Device tokens are always 64 hexadecimal characters
- **Note**: Currently not used for access verification (Variant 1 architecture)

### Important Notes

- **Verify always returns 200**: The decision is in the `decision` field (ALLOW/DENY)
- **Access verification uses user_session_token**: NOT device tokens
- **RBAC enforced**: Users must have explicit `AccessPermission` (user or group-based)
- **Authorization header**: Use `Authorization: Token <user_token>` for authenticated endpoints (`/devices/*`)
- **QR payload**: Can be used to transfer user_session_token to ESP32
- **Rate limiting**: Configurable via `ACCESS_VERIFY_RATE` setting (default: 30/second)

---

## Smoke Test (Variant 1: user_session_token + RBAC)

Complete end-to-end test scenario:

```bash
# 1. Get user session token
USER_TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin" | jq -r '.token')

echo "User token: $USER_TOKEN"

# 2. Create gate and grant permission to user's group (via Django shell)
docker-compose exec web python manage.py shell << 'PY'
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.access.models import AccessPoint, AccessPermission

User = get_user_model()

# Get or create user
u = User.objects.get(username="admin")

# Create group and add user to it
g, _ = Group.objects.get_or_create(name="ADMINS")
u.groups.add(g)

# Create gate
gate, _ = AccessPoint.objects.get_or_create(
    code="gate-01", 
    defaults={"name": "Main Gate"}
)

# Grant permission to group
AccessPermission.objects.get_or_create(
    access_point=gate, 
    group=g, 
    defaults={"allow": True}
)

print("✅ Setup complete: gate-01 accessible by ADMINS group")
PY

# 3. Test access verification with user token
echo -e "\n🔐 Testing access verification..."
curl -X POST http://localhost:8001/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d "{\"gate_id\":\"gate-01\",\"token\":\"$USER_TOKEN\"}" | jq

# Expected response:
# {
#   "decision": "ALLOW",
#   "reason": "OK",
#   "duration_ms": 800
# }
```

### Alternative: Direct user permission

```bash
# Grant permission directly to user (instead of group)
docker-compose exec web python manage.py shell << 'PY'
from django.contrib.auth import get_user_model
from apps.access.models import AccessPoint, AccessPermission

User = get_user_model()
u = User.objects.get(username="admin")
gate = AccessPoint.objects.get(code="gate-01")

AccessPermission.objects.get_or_create(
    access_point=gate,
    user=u,
    defaults={"allow": True}
)

print("✅ Direct user permission granted")
PY
```

### Test DENY scenarios

```bash
# Test with invalid token
curl -X POST http://localhost:8001/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d '{"gate_id":"gate-01","token":"invalid_token_123"}' | jq
# Expected: {"decision": "DENY", "reason": "TOKEN_INVALID"}

# Test with unknown gate
curl -X POST http://localhost:8001/api/v1/access/verify \
  -H "Content-Type: application/json" \
  -d "{\"gate_id\":\"gate-unknown\",\"token\":\"$USER_TOKEN\"}" | jq
# Expected: {"decision": "DENY", "reason": "UNKNOWN_GATE"}

# Test with no permission (create user without permissions)
docker-compose exec web python manage.py shell << 'PY'
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
u, _ = User.objects.get_or_create(username="noperm", defaults={"is_active": True})
u.set_password("test123")
u.save()
token, _ = Token.objects.get_or_create(user=u)
print(f"No-permission user token: {token.key}")
PY

# Use the printed token to test NO_PERMISSION
# curl -X POST http://localhost:8001/api/v1/access/verify \
#   -H "Content-Type: application/json" \
#   -d '{"gate_id":"gate-01","token":"<TOKEN_FROM_ABOVE>"}' | jq
# Expected: {"decision": "DENY", "reason": "NO_PERMISSION"}
```

---

## Production Deployment

**Environment variables for production:**

```bash
DJANGO_SETTINGS_MODULE=accessproj.settings.prod
DJANGO_SECRET_KEY=<random-secret-key>
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
ACCESS_VERIFY_RATE=100/second
```

**Production mode automatically uses:**
- Gunicorn with 4 workers
- HTTPS enforcement (SECURE_SSL_REDIRECT)
- HSTS with 1-year max-age
- Secure cookies (httponly, secure flags)
- Security headers (XSS, content-type sniffing protection)
