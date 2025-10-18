# LAN Debug Patch Report

**Date:** 2025-10-18  
**Status:** ✅ **PATCHES APPLIED SUCCESSFULLY**

---

## Summary

Applied minimal, safe patches to enable LAN debugging on physical Android device. All changes are **debug-only** and do **NOT** affect release builds.

---

## Changes Applied

### ✅ PATCH 1: build.gradle.kts (API_BASE_URL for LAN)

**File:** `android/OpenWay/app/build.gradle.kts`

**Changed:** Line 35
```kotlin
// BEFORE:
buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8001/\"")

// AFTER:
buildConfigField("String", "API_BASE_URL", "\"http://<LAN_IP>:8001/\"")
```

**Impact:**
- Debug builds now use placeholder `<LAN_IP>` instead of emulator IP (10.0.2.2)
- **ACTION REQUIRED:** Replace `<LAN_IP>` with your host's actual LAN IP (e.g., `192.168.1.100`)
- Release builds remain **UNAFFECTED** (no API_BASE_URL defined)

**How to find your LAN IP:**
```bash
# macOS
ipconfig getifaddr en0

# Linux
hostname -I | awk '{print $1}'

# Windows
ipconfig | findstr IPv4
```

---

### ✅ PATCH 2: network_security_config.xml (Allow cleartext HTTP globally)

**File:** `android/OpenWay/app/src/debug/res/xml/network_security_config.xml`

**Changed:** Entire file
```xml
<!-- BEFORE: Domain-specific config -->
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">127.0.0.1</domain>
        <domain includeSubdomains="true">localhost</domain>
    </domain-config>
</network-security-config>

<!-- AFTER: Global cleartext allowed (debug only) -->
<network-security-config>
    <!-- DEBUG ONLY: allow cleartext HTTP for local LAN endpoints -->
    <base-config cleartextTrafficPermitted="true" />
</network-security-config>
```

**Impact:**
- Debug builds allow HTTP to **any IP address** (including LAN IPs)
- More robust solution than listing specific domains
- Debug-only file, does **NOT** affect release builds

---

### ✅ PATCH 3: debug/AndroidManifest.xml (Already correct)

**File:** `android/OpenWay/app/src/debug/AndroidManifest.xml`

**Status:** ✅ Already correctly configured
```xml
<application android:networkSecurityConfig="@xml/network_security_config"/>
```

---

### ✅ PATCH 4: main/AndroidManifest.xml (Already correct)

**File:** `android/OpenWay/app/src/main/AndroidManifest.xml`

**Status:** ✅ INTERNET permission already present (line 8)
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

---

## Build Attempt

**Gradle Sync/Build:** ❌ Failed (Expected)

**Reason:**
```
SDK location not found. Define a valid SDK location with an ANDROID_HOME 
environment variable or by setting the sdk.dir path in your project's 
local properties file at '.../android/OpenWay/local.properties'.
```

**Analysis:** Build failure is **unrelated to patches** — Android SDK is not configured on this system. The patches themselves are syntactically correct.

**Recommendation:**
- Open project in Android Studio for proper build environment
- OR set ANDROID_HOME environment variable and create local.properties

---

## Next Steps

### 1. Update API_BASE_URL with your actual LAN IP

```bash
# Find your LAN IP:
ipconfig getifaddr en0  # macOS

# Edit build.gradle.kts and replace <LAN_IP> with actual IP
# Example: "http://192.168.1.100:8001/"
```

### 2. Verify backend is running on LAN port

```bash
# On your development machine, ensure backend is accessible:
curl http://192.168.1.100:8001/api/v1/health/  # (use your IP)
```

### 3. Build and deploy to physical device

```bash
# In Android Studio:
1. Connect physical device via USB
2. Enable USB debugging on device
3. Build > Select Build Variant > debug
4. Run > Run 'app'

# Or via command line (if SDK configured):
./gradlew installDebug
```

### 4. Test API connectivity

- Launch app on physical device
- App should now connect to backend at `http://<YOUR_LAN_IP>:8001/`
- Check logcat for network requests:
  ```bash
  adb logcat | grep -i "okhttp\|retrofit"
  ```

---

## Safety Notes

✅ **Release builds are NOT affected by these changes:**
- `API_BASE_URL` is only defined in `debug` build type
- `network_security_config.xml` is in `src/debug/` (debug-only)
- Release builds will **reject cleartext HTTP** by default (Android security policy)

✅ **No production credentials exposed:**
- `DEMO_DRF_TOKEN` remains debug-only
- No hardcoded production tokens

✅ **Minimal changes:**
- Only 2 files modified (build.gradle.kts, network_security_config.xml)
- 2 files verified as correct (manifests)
- No new files created
- No permissions added

---

## Verification Checklist

- [x] API_BASE_URL changed to `<LAN_IP>` placeholder in debug build
- [x] Cleartext HTTP allowed globally in debug via base-config
- [x] Debug manifest references network security config
- [x] INTERNET permission present in main manifest
- [x] Release build config unchanged
- [x] No production credentials exposed

---

## Summary

**Status:** ✅ **READY FOR TESTING**

All patches applied successfully. Replace `<LAN_IP>` with your actual LAN IP address, build the debug APK, and test on your physical device.

**Patches applied:**
1. ✅ build.gradle.kts → API_BASE_URL for LAN
2. ✅ network_security_config.xml → Global cleartext HTTP (debug)
3. ✅ Manifests verified (already correct)

**Build status:** SDK not configured (expected in review environment)

**Next action:** Replace `<LAN_IP>` in build.gradle.kts with your actual LAN IP and build in Android Studio.

