
# Протокол обмена (HCE + PN532)

## Сценарий
- Телефон (Android) эмулирует карту (**HCE**).
- Контроллер (ESP32 + PN532) инициирует обмен APDU.
- Контроллер шлёт `nonce` и `doorId`, телефон отвечает `payload + signature`.
- Контроллер (онлайн) отправляет пакет на бэкенд `/api/access/verify` и получает решение `allow/deny`.

## AID
Задайте собственный AID (пример): `F0010203040506`.

## APDU (TLV-поле внутри данных)
**Запрос (ридер → телефон)**:
```
CLA=0x80, INS=0x10 (GET_CHALLENGE), Data(TLV):
  0x01: doorId (ASCII)
  0x02: nonce (16 bytes random)
```

**Ответ (телефон → ридер)**:
```
Data (TLV):
  0x81: userId (ASCII)
  0x82: exp (unix, 8 bytes)
  0x83: payload = userId|doorId|nonce|exp   (bytes)
  0x84: sig = HMAC-SHA256(payload, sessionKey)  // MVP-вариант
      // офлайн-вариант: ECDSA(sig(payload), server_private_key), передаём kid
SW=0x9000
```

## Онлайновая проверка
Контроллер → Бэкенд `POST /api/access/verify`:
```json
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
```
Ответ:
```json
{ "decision":"allow", "reason":"ok", "open_seconds":3 }
```

## Минимум безопасности
- `nonce` для защиты от replay.
- TTL билета 30–60 сек.
- Привязка к `doorId`.
- Ограничение времени ответа APDU (десятки–сотни мс).
- HTTPS между контроллером и бэкендом.
