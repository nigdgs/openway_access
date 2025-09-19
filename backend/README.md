# Access Control MVP Backend

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
```bash
# Verify access at gate
POST /api/v1/access/verify
Content-Type: application/json

{
  "gate_id": "gate-01",
  "token": "<device_token>"
}

# Response (always 200):
{
  "decision": "ALLOW",  // or "DENY"
  "reason": "OK",       // or error reason
  "duration_ms": 800    // optional, may be null
}
```

#### 4. Health Check
```bash
# Check service health
GET /health

# Response: {"status": "ok"}
```

### Token Management Rules

- **Store the LATEST token**: Always use the most recent token returned by `/devices/register`
- **rotate=false**: Allows binding `android_device_id` without token rotation
- **rotate=true** (default): Generates new token on every call
- **Authorization header**: Use `Authorization: Token <user_token>` for authenticated endpoints

### Important Notes

- **Verify always returns 200**: The decision is in the `decision` field (ALLOW/DENY)
- **Token length**: Device tokens are always 64 hexadecimal characters
- **QR payload**: Currently equals the token (can be extended for custom formats)
- **Android device binding**: Use `rotate=false` to update `android_device_id` without changing the token
