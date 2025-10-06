# ESP32 Firmware Review - Executive Summary

**Project:** OpenWay Access Control System - ESP32 Firmware  
**Date:** 2025-10-04  
**Reviewer:** Senior Embedded/IoT Reviewer  
**Assessment:** 🔴 **PROTOTYPE ONLY - NOT PRODUCTION READY**

---

## 📊 Overall Assessment

| Category | Rating | Status |
|----------|--------|--------|
| **Security** | 🔴 CRITICAL | HTTP only, hardcoded secrets |
| **Reliability** | 🔴 CRITICAL | No error handling, no watchdog |
| **Protocol** | 🔴 CRITICAL | Wrong API format |
| **Code Quality** | 🟡 MEDIUM | Simple but needs structure |
| **Memory Management** | 🟡 MEDIUM | No leak protection |
| **Power Management** | 🔴 CRITICAL | Not implemented |
| **Configurability** | 🔴 CRITICAL | Hardcoded values |
| **Testing** | 🔴 CRITICAL | None |

**Overall Verdict:** ❌ **NOT PRODUCTION READY** - Prototype with critical security and reliability issues

---

## 🎯 Executive Summary

The ESP32 firmware exists only as a **basic prototype** demonstrating NFC reading and HTTP communication. It lacks essential production features including:

1. **Security** - No HTTPS, no certificate validation, hardcoded credentials
2. **Reliability** - No error handling, no recovery mechanisms, no watchdog
3. **Protocol Compliance** - Incorrect API payload format vs backend requirements
4. **Production Features** - No OTA, no logging, no configuration management

**Critical Gap:** This firmware will fail in production due to security vulnerabilities, lack of error recovery, and protocol mismatches with the backend.

---

## 🔴 Critical Issues (Blocking Production)

### Security Vulnerabilities

| # | Issue | Severity | Impact | CVSS | Fix Effort |
|---|-------|----------|--------|------|------------|
| 1 | **HTTP instead of HTTPS** | 🔴 CRITICAL | Token interception, MITM | 9.8 | 8h |
| 2 | **Hardcoded WiFi credentials** | 🔴 CRITICAL | Credential exposure in firmware | 9.1 | 4h |
| 3 | **Hardcoded API URL** | 🔴 HIGH | Cannot change backend | 6.5 | 2h |
| 4 | **No certificate validation** | 🔴 CRITICAL | MITM attacks | 9.1 | 4h |
| 5 | **Plain text token transmission** | 🔴 CRITICAL | Token theft | 9.8 | Covered by #1 |
| 6 | **No NTP time sync** | 🟡 MEDIUM | Timestamps unreliable | 4.2 | 2h |

**Total Security Effort:** ~20 hours

### Reliability Issues

| # | Issue | Severity | Impact | Fix Effort |
|---|-------|----------|--------|------------|
| 7 | **No watchdog timer** | 🔴 CRITICAL | System hangs forever | 2h |
| 8 | **Infinite loop on PN532 failure** | 🔴 CRITICAL | Device bricked if NFC fails | 1h |
| 9 | **No WiFi reconnection** | 🔴 HIGH | Fails on network drop | 4h |
| 10 | **No HTTP timeout** | 🟡 MEDIUM | Hangs on slow network | 1h |
| 11 | **No retry logic** | 🟡 MEDIUM | Single failure = no access | 3h |
| 12 | **Blocking delays** | 🟡 LOW | Poor responsiveness | 2h |
| 13 | **No heap monitoring** | 🟡 MEDIUM | Memory leaks undetected | 2h |

**Total Reliability Effort:** ~15 hours

### Protocol Issues

| # | Issue | Severity | Impact | Fix Effort |
|---|-------|----------|--------|------------|
| 14 | **Wrong API payload format** | 🔴 CRITICAL | Backend rejects requests | 2h |
| 15 | **Incorrect endpoint** | 🔴 HIGH | Wrong URL path | 1h |
| 16 | **No request ID** | 🟡 MEDIUM | Cannot track retries | 1h |
| 17 | **No error response handling** | 🟡 MEDIUM | Cannot handle DENY/RATE_LIMIT | 2h |

**Total Protocol Effort:** ~6 hours

**Grand Total:** ~41 hours (1 week of development)

---

## 📋 Detailed Code Review

### Current Implementation (main.cpp - 59 lines)

```cpp
// ❌ CRITICAL: Hardcoded credentials
const char* WIFI_SSID = "YourWiFi";  // Exposed in firmware binary
const char* WIFI_PASS = "YourPass";  // Plaintext password!
const char* API_BASE  = "http://10.0.2.2:8000/api";  // HTTP not HTTPS!
```

**Issues:**
1. Credentials extractable from firmware binary (strings command)
2. HTTP = plaintext transmission = token theft possible
3. 10.0.2.2 is Android emulator localhost (not production URL)

---

### WiFi Connection (lines 23-26)

```cpp
WiFi.begin(WIFI_SSID, WIFI_PASS);
Serial.print("WiFi connecting");
while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print("."); 
}
```

**Issues:**
- ❌ No connection timeout (infinite loop if WiFi unavailable)
- ❌ No reconnection logic (fails permanently if WiFi drops)
- ❌ Blocking delay (unresponsive during connection)
- ❌ No fallback AP mode for configuration

**Recommendation:**
```cpp
unsigned long wifiStartTime = millis();
const unsigned long WIFI_TIMEOUT = 30000; // 30 seconds

WiFi.begin(WIFI_SSID, WIFI_PASS);
while (WiFi.status() != WL_CONNECTED) {
    if (millis() - wifiStartTime > WIFI_TIMEOUT) {
        Serial.println("WiFi timeout, restarting...");
        ESP.restart();
    }
    delay(500);
}

// In loop: check connection and reconnect
if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    WiFi.reconnect();
}
```

---

### NFC Initialization (lines 28-32)

```cpp
nfc.begin();
uint32_t ver = nfc.getFirmwareVersion();
if (!ver) { 
    Serial.println("PN532 not found"); 
    while(true) delay(1000);  // ❌ CRITICAL: Hangs forever!
}
```

**Issues:**
- 🔴 **CRITICAL:** `while(true)` loop = device bricked permanently
- ❌ No retry attempts
- ❌ No fallback mode
- ❌ No watchdog to recover

**Recommendation:**
```cpp
int nfcRetries = 3;
while (nfcRetries > 0) {
    nfc.begin();
    uint32_t ver = nfc.getFirmwareVersion();
    if (ver) {
        Serial.println("PN532 ready");
        break;
    }
    Serial.printf("PN532 init failed, retries left: %d\n", --nfcRetries);
    delay(1000);
}

if (nfcRetries == 0) {
    Serial.println("PN532 init failed, restarting ESP32...");
    ESP.restart();
}
```

---

### NFC Reading (lines 36-40)

```cpp
uint8_t uid[7]; uint8_t uidLen;
if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLen)) {
    String token="";
    for (int i=0;i<uidLen;i++){ 
        if (uid[i]<16) token+="0"; 
        token+=String(uid[i],HEX); 
    }
```

**Issues:**
- ⚠️ Reading UID instead of APDU data from phone
- ⚠️ UID is not the user token!
- ❌ Should initiate HCE communication with Android app
- ❌ No validation of token format

**Expected Flow (from backend docs):**
1. Android app stores `user_session_token` (DRF Token) from `/api/v1/auth/token`
2. ESP32 reads this token via NFC HCE (not UID!)
3. ESP32 sends token to `/api/v1/access/verify`

**Recommendation:**
- Implement proper HCE/APDU protocol to read token from Android
- Validate token format (not just hex UID)
- Store token temporarily for verification

---

### HTTP Request (lines 42-54)

```cpp
if (WiFi.status()==WL_CONNECTED) {
    HTTPClient http;
    http.begin(String(API_BASE)+"/access/verify");  // ❌ Wrong path!
    http.addHeader("Content-Type","application/json");
    
    // ❌ CRITICAL: Wrong payload format!
    String body = String("{\"door_id\":\"D-1\",\"ts\":1693567200,"
                         "\"apdu\":{\"user_id\":\"U-1\",\"exp\":9999999999,"
                         "\"payload_b64\":\"Zm9v\",\"sig_b64\":\"YmFy\"},"
                         "\"controller_info\":{\"id\":\"C-1\",\"fw\":\"1.0.0\"}}");
    
    int code = http.POST(body);
    String resp = http.getString();
    http.end();
    Serial.printf("VERIFY HTTP %d %s\n", code, resp.c_str());
}
```

**Multiple Critical Issues:**

1. **Wrong Endpoint:**
   - Current: `/api/access/verify`
   - Correct: `/api/v1/access/verify`

2. **Wrong Payload Format:**
   Current (incorrect):
   ```json
   {
       "door_id": "D-1",
       "ts": 1693567200,
       "apdu": {...},
       "controller_info": {...}
   }
   ```
   
   Expected (from backend):
   ```json
   {
       "gate_id": "GATE_001",
       "token": "user_session_token_from_android"
   }
   ```

3. **No HTTPS:**
   - Uses `http://` instead of `https://`
   - WiFiClientSecure not used
   - No certificate validation

4. **No Error Handling:**
   - No check if `code == 200`
   - No parsing of response JSON
   - No handling of `decision: DENY`

5. **No Timeout:**
   - HTTP request can hang indefinitely

6. **No Retry Logic:**
   - Single failure = access denied (poor UX)

---

## 🔒 Security Analysis

### Threat Model

| Threat | Current Risk | Impact | Mitigation |
|--------|--------------|--------|------------|
| **Man-in-the-Middle (MITM)** | 🔴 HIGH | Token theft, access bypass | HTTPS + cert pinning |
| **Firmware Extraction** | 🔴 HIGH | WiFi/API credentials exposed | Remove hardcoded secrets |
| **Replay Attacks** | 🟡 MEDIUM | Reuse captured packets | Add nonce/timestamp |
| **Physical Tampering** | 🟡 MEDIUM | Direct hardware access | Secure boot, flash encryption |
| **Network Sniffing** | 🔴 HIGH | Token interception | HTTPS only |
| **Denial of Service** | 🟡 MEDIUM | Flood with requests | Rate limiting (backend handles) |

### Required Security Measures

#### 1. HTTPS with Certificate Validation

```cpp
#include <WiFiClientSecure.h>

WiFiClientSecure client;

// Certificate pinning (SHA-256 fingerprint)
const char* rootCACertificate = \
"-----BEGIN CERTIFICATE-----\n" \
"MIIDdzCC... (full cert)\n" \
"-----END CERTIFICATE-----\n";

void setup() {
    client.setCACert(rootCACertificate);
    // OR use fingerprint pinning:
    client.setFingerprint("AA BB CC DD ...");
}

void makeRequest() {
    HTTPClient https;
    https.begin(client, API_BASE "/v1/access/verify");
    https.setTimeout(10000); // 10 second timeout
    
    int httpCode = https.POST(payload);
    if (httpCode == 200) {
        String response = https.getString();
        // Parse JSON response
    }
    https.end();
}
```

#### 2. Configuration via EEPROM/SPIFFS

```cpp
#include <Preferences.h>

Preferences prefs;

void loadConfig() {
    prefs.begin("openway", false);
    String ssid = prefs.getString("wifi_ssid", "");
    String pass = prefs.getString("wifi_pass", "");
    String apiUrl = prefs.getString("api_url", "");
    String gateId = prefs.getString("gate_id", "");
    prefs.end();
}

// Configuration mode via AP
void setupConfigPortal() {
    WiFi.softAP("OpenWay-Config");
    // Start web server for configuration
}
```

#### 3. Secure Token Handling

```cpp
// Never log full token!
void logToken(const String& token) {
    if (token.length() > 8) {
        Serial.printf("Token: %s...%s\n", 
                      token.substring(0, 4).c_str(),
                      token.substring(token.length()-4).c_str());
    }
}

// Validate token format
bool isValidToken(const String& token) {
    // DRF tokens are 40 hex characters
    if (token.length() != 40) return false;
    for (char c : token) {
        if (!isxdigit(c)) return false;
    }
    return true;
}
```

---

## 🛡️ Reliability Improvements

### 1. Watchdog Timer

```cpp
#include "esp_task_wdt.h"

#define WDT_TIMEOUT 30  // 30 seconds

void setup() {
    // Enable watchdog
    esp_task_wdt_init(WDT_TIMEOUT, true);
    esp_task_wdt_add(NULL);
}

void loop() {
    // Reset watchdog periodically
    esp_task_wdt_reset();
    
    // Your code here...
}
```

### 2. Connection Resilience

```cpp
unsigned long lastWifiCheck = 0;
const unsigned long WIFI_CHECK_INTERVAL = 30000; // 30 seconds

void loop() {
    if (millis() - lastWifiCheck > WIFI_CHECK_INTERVAL) {
        lastWifiCheck = millis();
        
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("WiFi disconnected, reconnecting...");
            WiFi.disconnect();
            WiFi.reconnect();
            
            unsigned long reconnectStart = millis();
            while (WiFi.status() != WL_CONNECTED && 
                   millis() - reconnectStart < 10000) {
                delay(500);
            }
            
            if (WiFi.status() != WL_CONNECTED) {
                Serial.println("Reconnect failed, restarting...");
                ESP.restart();
            }
        }
    }
}
```

### 3. Memory Monitoring

```cpp
void printMemoryStats() {
    Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
    Serial.printf("Min free heap: %d bytes\n", ESP.getMinFreeHeap());
    Serial.printf("Heap fragmentation: %d%%\n", 
                  ESP.getHeapFragmentation());
}

void loop() {
    // Check for low memory
    if (ESP.getFreeHeap() < 10000) {  // Less than 10KB free
        Serial.println("WARNING: Low memory!");
        // Consider restart or garbage collection
    }
}
```

### 4. Error Handling & Retry Logic

```cpp
bool verifyAccess(const String& gateId, const String& token) {
    const int MAX_RETRIES = 3;
    const int RETRY_DELAY_MS = 2000;
    
    for (int attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        Serial.printf("Verify attempt %d/%d\n", attempt, MAX_RETRIES);
        
        HTTPClient https;
        https.begin(client, API_BASE "/v1/access/verify");
        https.setTimeout(10000);
        https.addHeader("Content-Type", "application/json");
        
        String payload = "{\"gate_id\":\"" + gateId + 
                        "\",\"token\":\"" + token + "\"}";
        
        int httpCode = https.POST(payload);
        String response = https.getString();
        https.end();
        
        if (httpCode == 200) {
            // Parse JSON response
            // Check decision: ALLOW/DENY
            return parseResponse(response);
        } else if (httpCode == 429) {
            // Rate limited - wait longer
            Serial.println("Rate limited, waiting...");
            delay(RETRY_DELAY_MS * 2);
        } else {
            Serial.printf("HTTP error: %d\n", httpCode);
            if (attempt < MAX_RETRIES) {
                delay(RETRY_DELAY_MS);
            }
        }
    }
    
    Serial.println("All retry attempts failed");
    return false;  // DENY by default
}
```

---

## 📡 Correct Backend Protocol

### Backend API (from backend memory)

**Endpoint:** `POST /api/v1/access/verify`

**Request:**
```json
{
  "gate_id": "GATE_001",
  "token": "a1b2c3d4e5f6..."  // 40-char DRF token from Android
}
```

**Response (Always 200):**
```json
{
  "decision": "ALLOW",  // or "DENY"
  "reason": "OK",       // or "TOKEN_INVALID", "NO_PERMISSION", etc.
  "duration_ms": 800    // Only present if ALLOW
}
```

**Possible Reasons:**
- `OK` - Access granted
- `TOKEN_INVALID` - Invalid/expired token
- `NO_PERMISSION` - User lacks permission for this gate
- `UNKNOWN_GATE` - Gate ID not found
- `INVALID_REQUEST` - Malformed request
- `RATE_LIMIT` - Too many requests

### Correct Implementation

```cpp
#include <ArduinoJson.h>

struct VerifyResponse {
    String decision;  // "ALLOW" or "DENY"
    String reason;
    int duration_ms;
};

VerifyResponse verifyAccess(const String& gateId, const String& token) {
    HTTPClient https;
    WiFiClientSecure client;
    client.setCACert(rootCACert);
    
    https.begin(client, String(API_BASE) + "/v1/access/verify");
    https.setTimeout(10000);
    https.addHeader("Content-Type", "application/json");
    
    // Generate request ID for tracking
    String requestId = String(millis()) + "-" + String(random(1000, 9999));
    https.addHeader("X-Request-ID", requestId);
    
    // Proper payload format
    StaticJsonDocument<256> requestDoc;
    requestDoc["gate_id"] = gateId;
    requestDoc["token"] = token;
    
    String payload;
    serializeJson(requestDoc, payload);
    
    int httpCode = https.POST(payload);
    String response = https.getString();
    https.end();
    
    VerifyResponse result;
    result.decision = "DENY";  // Default to DENY
    result.reason = "NETWORK_ERROR";
    result.duration_ms = 0;
    
    if (httpCode == 200) {
        StaticJsonDocument<256> responseDoc;
        DeserializationError error = deserializeJson(responseDoc, response);
        
        if (!error) {
            result.decision = responseDoc["decision"].as<String>();
            result.reason = responseDoc["reason"].as<String>();
            if (responseDoc.containsKey("duration_ms")) {
                result.duration_ms = responseDoc["duration_ms"];
            }
        }
    }
    
    Serial.printf("Verify: %s - %s (HTTP %d)\n", 
                  result.decision.c_str(), 
                  result.reason.c_str(), 
                  httpCode);
    
    return result;
}
```

---

## 🔧 Recommended Architecture

### File Structure

```
firmware/
├── platformio.ini
├── src/
│   ├── main.cpp           - Main entry point
│   ├── config.h           - Configuration constants
│   ├── wifi_manager.cpp   - WiFi connection & reconnection
│   ├── nfc_reader.cpp     - NFC/HCE communication
│   ├── api_client.cpp     - HTTPS API communication
│   ├── gate_controller.cpp - Gate control logic
│   └── logger.cpp         - Structured logging
├── data/
│   ├── config.json        - Configuration file (uploaded to SPIFFS)
│   └── ca_cert.pem        - CA certificate
└── test/
    └── test_main.cpp      - Unit tests
```

### Enhanced platformio.ini

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200

; Compiler flags
build_flags = 
    -Wall
    -Wextra
    -Werror
    -DCORE_DEBUG_LEVEL=4
    -DBOARD_HAS_PSRAM

; Dependencies
lib_deps =
    adafruit/Adafruit PN532 @ ^1.3.3
    bblanchon/ArduinoJson @ ^7.0.0
    
; Upload settings
upload_speed = 921600

; Monitoring
monitor_filters = esp32_exception_decoder

; Tests
test_framework = unity
```

---

## 📊 Implementation Roadmap

### Phase 1: Security Foundation (Week 1)

**Priority:** 🔴 CRITICAL

1. **Implement HTTPS**
   - Add WiFiClientSecure
   - Implement certificate validation
   - Add fingerprint pinning
   - Test with backend

2. **Remove Hardcoded Secrets**
   - Create config.h template
   - Implement EEPROM/Preferences storage
   - Add configuration portal (AP mode)
   - Secure credential storage

3. **Fix Backend Protocol**
   - Correct endpoint path
   - Proper JSON payload format
   - Response parsing
   - Error code handling

**Deliverables:**
- Secure HTTPS communication
- Configurable WiFi/API settings
- Correct backend integration

---

### Phase 2: Reliability (Week 2)

**Priority:** 🔴 CRITICAL

4. **Add Watchdog**
   - Enable ESP32 watchdog timer
   - Periodic reset in loop
   - Crash recovery

5. **Error Handling**
   - Remove infinite loops
   - Add retry logic (exponential backoff)
   - Timeout handling
   - Graceful degradation

6. **Connection Resilience**
   - WiFi reconnection logic
   - HTTP timeout configuration
   - Network status monitoring
   - Automatic restart on fatal errors

**Deliverables:**
- System that recovers from errors
- No permanent hangs
- Automatic reconnection

---

### Phase 3: NFC/HCE Protocol (Week 3)

**Priority:** 🔴 HIGH

7. **Implement Proper NFC Communication**
   - HCE protocol support
   - APDU command/response
   - Token extraction from Android
   - Validation of token format

8. **Token Handling**
   - Secure token storage (temporary)
   - Token validation
   - Secure logging (masked tokens)

**Deliverables:**
- Correct token reading from Android NFC
- Proper HCE communication

---

### Phase 4: Production Features (Week 4)

**Priority:** 🟡 HIGH

9. **Logging & Monitoring**
   - Structured logging
   - Log levels (DEBUG/INFO/WARN/ERROR)
   - Remote logging (optional)
   - Performance metrics

10. **OTA Updates**
    - OTA update capability
    - Version management
    - Rollback on failure
    - Secure update (signed firmware)

11. **Power Management**
    - Sleep modes
    - Wake on NFC
    - Battery optimization (if applicable)

**Deliverables:**
- Production-ready logging
- OTA update capability
- Optimized power consumption

---

### Phase 5: Testing & Polish (Week 5)

**Priority:** 🟡 MEDIUM

12. **Testing**
    - Unit tests (PlatformIO Test)
    - Integration tests with backend
    - Stress testing (reconnections)
    - Memory leak testing

13. **Documentation**
    - Hardware setup guide
    - Configuration guide
    - API documentation
    - Troubleshooting guide

14. **Optimization**
    - Code refactoring
    - Memory optimization
    - Response time optimization
    - Code size reduction

**Deliverables:**
- Tested, documented firmware
- Deployment guide
- Troubleshooting procedures

---

## 📈 Effort Estimation

| Phase | Component | Effort (hours) | Priority |
|-------|-----------|----------------|----------|
| 1 | HTTPS Implementation | 8h | 🔴 Critical |
| 1 | Remove Hardcoded Secrets | 4h | 🔴 Critical |
| 1 | Fix Backend Protocol | 2h | 🔴 Critical |
| 2 | Watchdog & Recovery | 4h | 🔴 Critical |
| 2 | Error Handling | 6h | 🔴 Critical |
| 2 | Connection Resilience | 5h | 🔴 Critical |
| 3 | NFC/HCE Protocol | 12h | 🔴 High |
| 3 | Token Handling | 4h | 🔴 High |
| 4 | Logging | 4h | 🟡 High |
| 4 | OTA Updates | 8h | 🟡 High |
| 4 | Power Management | 6h | 🟡 Medium |
| 5 | Testing | 8h | 🟡 Medium |
| 5 | Documentation | 4h | 🟡 Medium |
| 5 | Optimization | 6h | 🟡 Low |
| **TOTAL** | | **81 hours** | **~2 months** |

---

## 🎓 Key Takeaways

### What Exists ✅
- Basic WiFi connection
- Basic NFC reader initialization
- Basic HTTP POST

### What's Missing ❌
- **Security** - HTTPS, certificate validation, secure config
- **Reliability** - Error handling, watchdog, reconnection
- **Protocol** - Correct API format and parsing
- **Production Features** - OTA, logging, monitoring
- **Testing** - No tests whatsoever

### Production Readiness Score

| Category | Score | Max |
|----------|-------|-----|
| Security | 1/10 | 10 |
| Reliability | 2/10 | 10 |
| Protocol | 2/10 | 10 |
| Features | 2/10 | 10 |
| Testing | 0/10 | 10 |
| **TOTAL** | **7/50** | **50** |

**Grade:** F (14%) - **❌ NOT PRODUCTION READY**

---

## 🚨 Critical Warnings

### DO NOT deploy this firmware to production!

**Reasons:**
1. 🔴 **Security risk:** Plaintext token transmission
2. 🔴 **Reliability risk:** Infinite loops = bricked devices
3. 🔴 **Protocol mismatch:** Backend will reject requests
4. 🔴 **No recovery:** Permanent failures require physical access

### Deployment Checklist

Before production deployment:
- [ ] HTTPS with certificate validation implemented
- [ ] All secrets removed from code
- [ ] Configuration portal implemented
- [ ] Watchdog timer enabled
- [ ] All infinite loops removed
- [ ] Proper error handling and recovery
- [ ] Backend protocol correctly implemented
- [ ] Retry logic with exponential backoff
- [ ] Connection resilience tested
- [ ] Memory leaks tested
- [ ] OTA updates working
- [ ] Logging implemented
- [ ] Documentation complete
- [ ] Field testing completed (100+ operations)
- [ ] Security audit passed

---

## 📚 Additional Resources

### ESP32 Security Best Practices
- ESP-IDF Security Guide: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/security/
- HTTPS on ESP32: https://github.com/espressif/arduino-esp32/tree/master/libraries/HTTPClient
- Secure Boot: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/security/secure-boot-v2.html

### NFC/HCE Resources
- PN532 Datasheet: https://www.nxp.com/docs/en/user-guide/141520.pdf
- ISO/IEC 14443 Standard (NFC protocol)
- Android HCE Integration: https://developer.android.com/guide/topics/connectivity/nfc/hce

### PlatformIO Resources
- PlatformIO Testing: https://docs.platformio.org/en/latest/plus/unit-testing.html
- OTA Updates: https://docs.platformio.org/en/latest/platforms/espressif32.html#over-the-air-ota-update

---

**Review Status:** ✅ COMPLETE  
**Recommendation:** ❌ **NOT APPROVED** - Requires complete rewrite (~2 months)  
**Next Steps:** Follow Implementation Roadmap (Phases 1-5)

---

*Generated by: Senior Embedded/IoT Reviewer*  
*Date: 2025-10-04*  
*Branch: feature/android-review (to be renamed to feature/firmware-review)*

