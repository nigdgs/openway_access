# Direct Backend Integration Summary

## ✅ Completed Integration

### 1. BackendClient.kt
- **File**: `app/src/main/java/com/example/openway/net/BackendClient.kt`
- **Purpose**: HTTP client for direct backend calls (emulator mode)
- **Features**:
  - POST requests to `${baseUrl}/api/v1/access/verify`
  - JSON body: `{"gate_id": gateId, "token": token}`
  - Timeouts: connect=2s, read=3s
  - No retry on connection failure
  - Debug logging with HttpLoggingInterceptor (BASIC level)
  - Coroutines with Dispatchers.IO

### 2. PassService Extension
- **File**: `app/src/main/java/com/example/openway/domain/PassService.kt`
- **Changes**:
  - Added import: `import com.example.openway.net.BackendClient`
  - Extended `pass()` method with `directBackendBase: String? = null` parameter
  - **Logic**: 
    - If `directBackendBase != null` → calls `BackendClient.verify()`
    - If `directBackendBase == null` → calls `EspClient.enter()` (original behavior)
  - Maintains backward compatibility

### 3. MainActivity Integration
- **File**: `app/src/main/java/com/example/openway/MainActivity.kt`
- **Changes**:
  - Modified NFC button click handler
  - **New call**: `pass.pass(debug = BuildConfig.DEBUG, directBackendBase = "http://10.0.2.2:8001")`
  - Uses existing NFC button (no new UI elements)
  - Shows result via Toast: `"$decision / $reason"`
  - Maintains existing NFC toggle functionality

## 🔄 Integration Flow (Emulator Mode)

1. **App Launch**: MainActivity sets default ESP_IP and GATE_ID
2. **Login**: User logs in, demo token is saved to secure storage
3. **Main Screen**: User sees NFC button
4. **Pass Attempt**: User clicks NFC button
   - NFC state toggles (existing functionality)
   - **Direct backend call**: `POST http://10.0.2.2:8001/api/v1/access/verify`
   - Request body: `{"gate_id": "gate-01", "token": "demo_token_..."}`
   - Response: `{"decision": "ALLOW|DENY", "reason": "...", "duration_ms": 800}`
   - Result shown via Toast

## 🧪 Testing Checklist (Emulator)

- [ ] Backend running on `http://localhost:8001`
- [ ] Android emulator can reach `http://10.0.2.2:8001`
- [ ] App builds successfully
- [ ] Demo token is saved after login
- [ ] NFC button shows backend response in Toast
- [ ] Network requests logged in debug mode
- [ ] Error handling works (network failures, invalid responses)

## 📝 Key Features

- **Dual Mode**: Supports both ESP32 (original) and direct backend (emulator)
- **Minimal UI Changes**: Uses existing NFC button
- **Backward Compatibility**: Original ESP32 mode still works
- **Debug Support**: HttpLoggingInterceptor for network debugging
- **Error Handling**: Graceful fallback to "DENY/UNKNOWN"
- **Security**: No full token logging, only preview

## 🔧 Configuration

- **Emulator Backend URL**: `http://10.0.2.2:8001` (hardcoded for emulator)
- **API Endpoint**: `/api/v1/access/verify`
- **Request Format**: `{"gate_id": string, "token": string}`
- **Response Format**: `{"decision": string, "reason": string, "duration_ms": number}`

## 🚀 Usage

1. Start backend: `docker compose -f backend/compose.yml up -d`
2. Run Android app in emulator
3. Login with any credentials (demo token will be saved)
4. Click NFC button to test direct backend integration
5. Check Toast for response: "ALLOW/OK" or "DENY/REASON"

## ⚠️ Notes

- **Emulator Only**: `10.0.2.2` is emulator-specific (maps to host localhost)
- **Demo Token**: Currently uses temporary token for testing
- **No ESP32**: This mode bypasses ESP32 completely
- **Debug Mode**: Enable debug logging to see network requests
