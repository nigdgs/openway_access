
# Контракты API (черновик)

## POST /api/mobile/ticket
Выдать краткоживущий sessionKey (для HMAC) или параметры для подписи.
```json
RES 200:
{
  "user_id": "U-123",
  "exp": 1693567260,
  "session_key_b64": "base64(32 bytes)",
  "kid": "key-2025-09-A"
}
```

## POST /api/access/verify
Проверка подписи/TTL/прав доступа.
```json
REQ:
{
  "door_id": "D-1",
  "ts": 1693567200,
  "apdu": {
    "user_id": "U-123",
    "exp": 1693567260,
    "payload_b64": "base64(...)",
    "sig_b64": "base64(...)",
    "kid": "key-2025-09-A"
  },
  "controller_info": {"id":"C-1","fw":"1.0.0"}
}
RES 200 allow:
{ "decision":"allow", "reason":"ok", "open_seconds":3 }
RES 403 deny:
{ "decision":"deny", "reason":"expired/signature invalid/acl" }
```

## POST /api/events
Приём журналов от контроллера (пакетно).
```json
REQ:
{
  "controller_id":"C-1",
  "batch":[
    {"door_id":"D-1","ts":1693567200,"decision":"allow","user_id":"U-123","reason":"ok"},
    {"door_id":"D-1","ts":1693567210","decision":"deny","token_hash_prefix":"a1b2c3","reason":"sig invalid"}
  ]
}
RES:
{ "stored": 2 }
```

## GET /api/controllers/config
Конфиг для офлайн-режима (ключи, политика).
```json
RES:
{
  "keys":[{"kid":"key-2025-09-A","pub_pem":"-----BEGIN PUBLIC KEY-----...","not_after":1700000000,"revoked":false}],
  "policy":{"max_apdu_ms":200,"session_ttl":60}
}
```
