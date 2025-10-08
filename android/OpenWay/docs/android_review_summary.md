# Android Client Review - Executive Summary

**Project:** OpenWay Access Control System - Android Client  
**Date:** 2025-10-04  
**Reviewer:** Senior Android/Kotlin Reviewer  
**Branch:** feature/android-review  
**Assessment:** 🔴 **PROTOTYPE ONLY - NOT PRODUCTION READY**

---

## 📊 Overall Assessment

| Category | Rating | Status |
|----------|--------|--------|
| **Architecture** | 🔴 CRITICAL | No architecture - flat structure |
| **Security** | 🔴 CRITICAL | Zero security implementation |
| **NFC/HCE** | 🔴 CRITICAL | Not implemented |
| **BLE** | 🔴 CRITICAL | Not implemented |
| **API Integration** | 🔴 CRITICAL | Not implemented |
| **Data Storage** | 🔴 CRITICAL | Not implemented |
| **UI/UX** | 🟢 GOOD | Clean Compose UI (prototype) |
| **Testing** | 🔴 CRITICAL | Only template tests |

**Overall Verdict:** ❌ **NOT PRODUCTION READY** - This is a UI prototype with no functional implementation

---

## 🎯 Executive Summary

The Android client for OpenWay Access exists only as a **visual prototype** with **zero functional implementation** of the core access control features. While the UI is well-designed using Jetpack Compose, the application lacks:

1. **NFC/HCE Implementation** - The primary method of access control
2. **BLE Integration** - Alternative communication method
3. **Backend API Integration** - No authentication, no token management
4. **Security Implementation** - No encryption, secure storage, or permissions
5. **Architecture** - No MVVM/MVI, no ViewModels, no Repository pattern
6. **Data Persistence** - No token storage, no offline capability

**Critical Gap:** This application cannot function as an access control system in its current state. It requires complete development from scratch following the architecture described in backend documentation.

---

## 🔴 Critical Issues (Blocking Production)

### Must Have - Core Functionality Missing

| # | Issue | Severity | Impact | Est. Effort |
|---|-------|----------|--------|-------------|
| 1 | **NO NFC/HCE Implementation** | 🔴 BLOCKER | Cannot transmit tokens to readers | 40h |
| 2 | **NO BLE Implementation** | 🔴 BLOCKER | Cannot communicate with ESP32 | 32h |
| 3 | **NO API Integration** | 🔴 BLOCKER | Cannot authenticate users | 24h |
| 4 | **NO Token Storage** | 🔴 BLOCKER | Cannot persist user tokens | 16h |
| 5 | **NO Permissions Declared** | 🔴 BLOCKER | App will crash on feature use | 2h |
| 6 | **NO Security Implementation** | 🔴 CRITICAL | Tokens exposed, no encryption | 24h |
| 7 | **NO Architecture** | 🔴 CRITICAL | Unmaintainable, no testability | 32h |
| 8 | **NO Error Handling** | 🔴 HIGH | Poor UX, crashes | 16h |
| 9 | **NO Offline Support** | 🔴 HIGH | Requires constant connectivity | 8h |
| 10 | **NO Logging/Analytics** | 🟡 MEDIUM | Cannot debug issues | 8h |

**Total Effort:** ~200 hours (5-6 weeks of development)

---

## 📋 Detailed Findings

### 1. NFC/HCE - Not Implemented ❌

**Required Implementation:**
- Host Card Emulation (HCE) service for token transmission
- NFC reader detection and communication
- APDU command handling (SELECT, READ RECORD)
- Token payload formatting
- Retry logic and timeout handling

**Current State:** NONE

**Backend Integration Required:**
According to backend memory, the flow should be:
1. User logs in → receives `user_session_token` (DRF Token)
2. Token stored securely (EncryptedSharedPreferences/Keystore)
3. Token transmitted via NFC HCE to ESP32
4. ESP32 calls `/api/v1/access/verify` with token

**Missing in Android:**
- HCE Service declaration in manifest
- AID filter configuration
- APDU processing logic
- Token encoding/formatting
- Error handling for NFC disabled/unavailable

**References:**
- Android HCE Guide: https://developer.android.com/guide/topics/connectivity/nfc/hce
- APDU Commands: ISO/IEC 7816-4

---

### 2. BLE - Not Implemented ❌

**Required Implementation:**
- BLE GATT client for ESP32 communication
- Service/Characteristic discovery
- Token write operation via GATT
- Connection state management
- Permissions: BLUETOOTH, BLUETOOTH_ADMIN, ACCESS_FINE_LOCATION (Android 12+)

**Current State:** NONE

**Expected Flow:**
1. Scan for ESP32 BLE peripheral
2. Connect to device
3. Discover GATT services
4. Write `user_session_token` to characteristic
5. Handle write confirmation/errors
6. Disconnect after transmission

**Missing:**
- BLE permissions in manifest
- Runtime permission requests (Android 12+)
- BLE scanning logic
- GATT client implementation
- Connection management
- MTU negotiation for large payloads

**Recommended Library:**
- Nordic BLE Library: `no.nordicsemi.android:ble:2.7.1`
- Provides: Connection manager, GATT abstraction, retry logic

---

### 3. API Integration - Not Implemented ❌

**Required Endpoints (from backend):**

#### POST /api/v1/auth/token
```kotlin
// Request
data class LoginRequest(
    val username: String,
    val password: String
)

// Response
data class LoginResponse(
    val token: String  // DRF Token for user session
)
```

#### POST /api/v1/devices/register
```kotlin
// Request (requires Token auth)
data class DeviceRegisterRequest(
    val android_device_id: String?,
    val rotate: Boolean = true
)

// Response
data class DeviceRegisterResponse(
    val device_id: Int,
    val token: String,        // Device auth token (NOT used in current architecture)
    val qr_payload: String
)
```

**Current State:** 
- ❌ NO Retrofit/OkHttp setup
- ❌ NO API service interface
- ❌ NO DTOs (Data Transfer Objects)
- ❌ NO Repository layer
- ❌ NO error handling
- ❌ NO token interceptor for authentication

**Required Implementation:**
```kotlin
// ApiService.kt
interface OpenWayApiService {
    @POST("api/v1/auth/token")
    suspend fun login(@Body request: LoginRequest): LoginResponse
    
    @POST("api/v1/devices/register")
    suspend fun registerDevice(@Body request: DeviceRegisterRequest): DeviceRegisterResponse
}

// Network module (Hilt)
@Module
object NetworkModule {
    @Provides
    fun provideOkHttp(authInterceptor: AuthInterceptor): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = if (BuildConfig.DEBUG) 
                    HttpLoggingInterceptor.Level.BODY 
                else 
                    HttpLoggingInterceptor.Level.NONE
            })
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }
    
    @Provides
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create())
            .build()
    }
}
```

---

### 4. Permissions - Not Declared ❌

**AndroidManifest.xml Current State:**
```xml
<manifest>
    <application>
        <!-- Only MainActivity, no permissions! -->
    </application>
</manifest>
```

**Required Permissions:**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- Internet for API calls -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    
    <!-- NFC/HCE -->
    <uses-permission android:name="android.permission.NFC" />
    <uses-feature 
        android:name="android.hardware.nfc.hce"
        android:required="true" />
    
    <!-- BLE (Android 12+) -->
    <uses-permission android:name="android.permission.BLUETOOTH" 
                     android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" 
                     android:maxSdkVersion="30" />
    
    <!-- Android 12+ BLE permissions -->
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    
    <!-- Location for BLE (required by Android) -->
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    
    <!-- Foreground service (for persistent BLE/NFC) -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />

    <application>
        <!-- HCE Service -->
        <service
            android:name=".nfc.AccessHceService"
            android:exported="true"
            android:permission="android.permission.BIND_NFC_SERVICE">
            <intent-filter>
                <action android:name="android.nfc.cardemulation.action.HOST_APDU_SERVICE"/>
            </intent-filter>
            <meta-data
                android:name="android.nfc.cardemulation.host_apdu_service"
                android:resource="@xml/apduservice"/>
        </service>
        
        <!-- Activities -->
        <activity android:name=".MainActivity" ... />
    </application>
</manifest>
```

**Runtime Permissions Handling:**
```kotlin
// Required for Android 12+ BLE
class MainActivity : ComponentActivity() {
    private val blePermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        when {
            permissions[Manifest.permission.BLUETOOTH_SCAN] == true &&
            permissions[Manifest.permission.BLUETOOTH_CONNECT] == true &&
            permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true -> {
                // Permissions granted
            }
            else -> {
                // Show rationale or disable BLE features
            }
        }
    }
}
```

---

### 5. Security Implementation - Missing ❌

**Current State:** ZERO security measures

**Required Security Measures:**

#### A. Token Storage (EncryptedSharedPreferences)
```kotlin
// TokenManager.kt
class TokenManager(private val context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
        
    private val encryptedPrefs = EncryptedSharedPreferences.create(
        context,
        "openway_secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    fun saveUserToken(token: String) {
        encryptedPrefs.edit()
            .putString("user_token", token)
            .apply()
    }
    
    fun getUserToken(): String? {
        return encryptedPrefs.getString("user_token", null)
    }
    
    fun clearToken() {
        encryptedPrefs.edit().remove("user_token").apply()
    }
}
```

#### B. Network Security Config
```xml
<!-- res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
    
    <!-- Certificate Pinning for backend -->
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">api.openway.example.com</domain>
        <pin-set expiration="2026-01-01">
            <pin digest="SHA-256">AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=</pin>
            <pin digest="SHA-256">BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=</pin>
        </pin-set>
    </domain-config>
    
    <!-- Allow cleartext for localhost (dev only) -->
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">127.0.0.1</domain>
    </domain-config>
</network-security-config>
```

```xml
<!-- AndroidManifest.xml -->
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
</application>
```

#### C. SSL Pinning in OkHttp
```kotlin
val certificatePinner = CertificatePinner.Builder()
    .add("api.openway.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    .add("api.openway.example.com", "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=")
    .build()

OkHttpClient.Builder()
    .certificatePinner(certificatePinner)
    .build()
```

#### D. ProGuard Rules (proguard-rules.pro)
```proguard
# Keep NFC HCE Service
-keep class com.example.openway.nfc.AccessHceService { *; }

# Keep API models
-keep class com.example.openway.data.model.** { *; }

# Retrofit
-keepattributes Signature, InnerClasses, EnclosingMethod
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}

# Moshi
-keep class kotlin.Metadata { *; }
-keep @com.squareup.moshi.JsonQualifier interface *

# Security - Don't obfuscate crypto classes
-keep class javax.crypto.** { *; }
-keep class java.security.** { *; }
```

---

### 6. Architecture - Not Implemented ❌

**Recommended Architecture: Clean Architecture + MVVM**

```
app/src/main/java/com/example/openway/
├── data/
│   ├── api/
│   │   ├── OpenWayApiService.kt
│   │   ├── dto/
│   │   │   ├── LoginRequest.kt
│   │   │   ├── LoginResponse.kt
│   │   │   └── DeviceRegisterRequest.kt
│   │   └── interceptor/
│   │       └── AuthInterceptor.kt
│   ├── repository/
│   │   ├── AuthRepository.kt
│   │   ├── DeviceRepository.kt
│   │   └── AccessRepository.kt
│   ├── local/
│   │   ├── TokenManager.kt
│   │   └── UserPreferences.kt
│   └── model/
│       ├── User.kt
│       └── AccessResult.kt
├── domain/
│   ├── usecase/
│   │   ├── LoginUseCase.kt
│   │   ├── RegisterDeviceUseCase.kt
│   │   └── TransmitTokenUseCase.kt
│   └── model/
│       └── DomainModels.kt
├── ui/
│   ├── login/
│   │   ├── LoginScreen.kt
│   │   ├── LoginViewModel.kt
│   │   └── LoginState.kt
│   ├── main/
│   │   ├── MainScreen.kt
│   │   ├── MainViewModel.kt
│   │   └── MainState.kt
│   ├── access/
│   │   ├── AccessScreen.kt
│   │   └── AccessViewModel.kt
│   ├── navigation/
│   │   └── NavGraph.kt
│   └── theme/
│       ├── Color.kt
│       ├── Theme.kt
│       └── Type.kt
├── nfc/
│   ├── AccessHceService.kt
│   ├── ApduHandler.kt
│   └── NfcManager.kt
├── ble/
│   ├── BleManager.kt
│   ├── GattCallback.kt
│   └── BleState.kt
└── di/
    ├── AppModule.kt
    ├── NetworkModule.kt
    └── StorageModule.kt
```

**Key Components:**

1. **ViewModel** - Manage UI state, handle business logic
2. **Repository** - Abstract data sources (API + local)
3. **UseCase** - Single responsibility business actions
4. **Dependency Injection** - Hilt for modularity
5. **State Management** - Sealed classes for UI states

---

### 7. Missing Dependencies

**Required build.gradle.kts additions:**

```kotlin
dependencies {
    // Network
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:5.0.0")
    implementation("com.squareup.okhttp3:logging-interceptor:5.0.0")
    
    // JSON
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    ksp("com.squareup.moshi:moshi-kotlin-codegen:1.15.1")
    
    // Dependency Injection
    implementation("com.google.dagger:hilt-android:2.52")
    ksp("com.google.dagger:hilt-compiler:2.52")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
    
    // Data Storage
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    
    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    
    // BLE (optional but recommended)
    implementation("no.nordicsemi.android:ble:2.7.1")
    
    // Logging
    implementation("com.jakewharton.timber:timber:5.0.1")
    
    // Testing
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
    testImplementation("app.cash.turbine:turbine:1.1.0")
    testImplementation("io.mockk:mockk:1.13.12")
}
```

---

## 🛠️ Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Priority: 🔴 CRITICAL**

1. **Setup Architecture**
   - Add Hilt for DI
   - Create data/domain/UI layers
   - Add ViewModels
   - Implement Repository pattern

2. **Add Dependencies**
   - Retrofit/OkHttp
   - Moshi
   - EncryptedSharedPreferences
   - Logging (Timber)

3. **Configure Security**
   - Network Security Config
   - Certificate pinning
   - ProGuard rules
   - BuildConfig for API URL

### Phase 2: Core Features (Week 3-4)

**Priority: 🔴 CRITICAL**

4. **Implement Authentication**
   - Login screen with ViewModel
   - API integration (POST /api/v1/auth/token)
   - Token storage (EncryptedSharedPreferences)
   - Error handling

5. **Implement Device Registration**
   - API integration (POST /api/v1/devices/register)
   - Device ID management
   - Token rotation logic

6. **Add Permissions**
   - Declare in manifest
   - Runtime permission requests
   - Permission denied handling

### Phase 3: NFC/HCE Implementation (Week 5)

**Priority: 🔴 CRITICAL**

7. **Implement HCE Service**
   - Create AccessHceService
   - Configure AID filter
   - APDU command handling
   - Token transmission logic

8. **NFC UI/UX**
   - NFC enabled/disabled detection
   - User instructions
   - Success/failure feedback
   - Retry mechanism

### Phase 4: BLE Implementation (Week 6)

**Priority: 🔴 CRITICAL**

9. **Implement BLE Manager**
   - Peripheral scanning
   - GATT client
   - Connection management
   - Token write operation

10. **BLE UI/UX**
    - Scanning indicator
    - Connection state feedback
    - Error handling
    - Retry logic

### Phase 5: Testing & Polish (Week 7-8)

**Priority: 🟡 HIGH**

11. **Add Tests**
    - Unit tests (ViewModels, Repositories, UseCases)
    - Integration tests (API, NFC, BLE)
    - UI tests (login flow, access flow)
    - Instrumented tests

12. **Polish & Optimization**
    - Offline support
    - Analytics/logging
    - Performance optimization
    - UI/UX improvements
    - Accessibility

---

## 📊 Risk Matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| No NFC/HCE implementation | Certain | Critical | 🔴 BLOCKER | Implement HCE service (Phase 3) |
| No BLE implementation | Certain | Critical | 🔴 BLOCKER | Implement BLE manager (Phase 4) |
| No API integration | Certain | Critical | 🔴 BLOCKER | Implement Retrofit client (Phase 2) |
| No token security | Certain | High | 🔴 CRITICAL | Add EncryptedSharedPrefs (Phase 1) |
| No architecture | Certain | High | 🔴 CRITICAL | Implement MVVM+Hilt (Phase 1) |
| Hardcoded strings (no i18n) | High | Low | 🟡 MEDIUM | Move to strings.xml (Phase 5) |
| No error handling | High | Medium | 🟡 MEDIUM | Add throughout (Phase 2-4) |

---

## 📝 Recommendations Summary

### Immediate Actions (Before Any Development):

1. 🔴 **Define Architecture** - Document the target architecture (MVVM, layers)
2. 🔴 **Create Technical Design** - Document NFC/HCE and BLE protocols
3. 🔴 **Setup Project Structure** - Create package structure for data/domain/UI
4. 🔴 **Add Build Configuration** - BuildConfig, flavors, signing
5. 🔴 **Add Security Config** - Network Security Config, certificate pins

### Development Priorities:

**Must Have (MVP):**
- Authentication (login → token)
- Token storage (encrypted)
- NFC HCE implementation
- Basic error handling
- Permissions

**Should Have (v1.0):**
- BLE implementation
- Offline support
- Device registration
- Comprehensive error handling
- Unit tests

**Nice to Have (v1.x):**
- Analytics
- Advanced UX features
- Performance optimization
- UI tests
- Accessibility

---

## 📈 Effort Estimation

| Component | Effort (hours) | Priority |
|-----------|----------------|----------|
| Architecture Setup | 16h | 🔴 Critical |
| Authentication + Token Storage | 24h | 🔴 Critical |
| NFC/HCE Implementation | 40h | 🔴 Critical |
| BLE Implementation | 32h | 🔴 Critical |
| API Integration | 24h | 🔴 Critical |
| Security (SSL pinning, encryption) | 16h | 🔴 Critical |
| Error Handling | 16h | 🟡 High |
| Testing | 32h | 🟡 High |
| UI/UX Polish | 16h | 🟢 Medium |
| Documentation | 8h | 🟢 Medium |
| **TOTAL** | **224 hours** | **~6-7 weeks** |

---

## ✅ Production Readiness Checklist

### Functionality
- [ ] User authentication implemented
- [ ] Token storage (encrypted) implemented
- [ ] NFC/HCE service implemented and tested
- [ ] BLE communication implemented and tested
- [ ] Device registration implemented
- [ ] Error handling comprehensive
- [ ] Offline support implemented
- [ ] Permission handling complete

### Security
- [ ] Network Security Config configured
- [ ] Certificate pinning enabled
- [ ] ProGuard/R8 enabled for release
- [ ] EncryptedSharedPreferences for tokens
- [ ] No hardcoded secrets
- [ ] SSL-only communication
- [ ] Signed release builds

### Architecture & Code Quality
- [ ] MVVM architecture implemented
- [ ] Dependency injection (Hilt) configured
- [ ] Repository pattern implemented
- [ ] ViewModels for all screens
- [ ] Clean separation of concerns
- [ ] Code coverage > 70%
- [ ] Lint warnings addressed
- [ ] Accessibility labels added

### Testing
- [ ] Unit tests for ViewModels
- [ ] Unit tests for Repositories
- [ ] Unit tests for UseCases
- [ ] Integration tests for API
- [ ] Integration tests for NFC/HCE
- [ ] Integration tests for BLE
- [ ] UI tests for critical flows
- [ ] Manual testing on multiple devices

### Deployment
- [ ] Build variants configured (dev/staging/prod)
- [ ] Signing configuration set up
- [ ] ProGuard rules optimized
- [ ] APK size optimized
- [ ] Crash reporting configured (Firebase Crashlytics)
- [ ] Analytics configured
- [ ] Release notes prepared

---

## 🎓 Key Takeaways

### What Exists ✅
- Clean Compose UI (prototype)
- Basic navigation structure
- Dark/light theme toggle
- Material3 theming

### What's Missing ❌
- **Everything functional** - NFC, BLE, API, authentication, security
- Architecture layers
- Data persistence
- Error handling
- Testing
- Security measures
- Proper Android development practices

### Production Readiness Score

| Category | Score | Max |
|----------|-------|-----|
| Functionality | 0/10 | 10 |
| Security | 0/10 | 10 |
| Architecture | 1/10 | 10 |
| Testing | 0/10 | 10 |
| UI/UX | 7/10 | 10 |
| **TOTAL** | **8/50** | **50** |

**Grade:** F (16%) - **❌ NOT PRODUCTION READY**

This is a UI mockup that requires **complete functional implementation**.

---

**Review Status:** ✅ COMPLETE  
**Recommendation:** ❌ **NOT APPROVED** - Requires full development cycle (~6-7 weeks)  
**Next Steps:** Follow Implementation Roadmap (Phases 1-5)

---

*Generated by: Senior Android/Kotlin Reviewer*  
*Date: 2025-10-04*  
*Branch: feature/android-review*

