# Android Token Flow Audit

**Дата:** 2025-10-18  
**Проект:** OpenWay Access - Android Client  
**Аудитор:** Token Flow Review  
**Цель:** Полная реконструкция токен-флоу без изменения кода

---

## TL;DR

**Источник токена:** `POST /api/v1/auth/token` через `LoginScreen` → `AuthRepository` → `AuthApi`  
**Хранилище:** Обычный `SharedPreferences` (`openway_prefs` / `user_token`) — **НЕ зашифрован**  
**Чтение:** `TokenProvider.getToken()` с fallback на `BuildConfig.DEMO_DRF_TOKEN` (debug-only)  
**Использование:**  
- HTTP verify: `VerifyRepository.verify(gateId, token)` → `POST /api/v1/access/verify`  
- BLE: `BleClient.sendToken(token)` → отправка на ESP32 по Bluetooth  

**Очистка:** `TokenProvider.clearToken()` при нажатии кнопки "Выйти" в `MainActivity.exitAcc()`  
**Безопасность:** 🔴 **НЕ ЗАЩИЩЁН** — plain SharedPreferences, несмотря на наличие `security-crypto` в зависимостях

---

## Архитектура токена (ASCII Flow)

```
┌──────────────┐
│ LoginScreen  │ (UI)
└──────┬───────┘
       │ 1. submitLogin()
       │    login: String, password: String
       ▼
┌──────────────────┐
│ AuthRepository   │
│ .login(context,  │
│  username, pwd)  │
└──────┬───────────┘
       │ 2. POST /api/v1/auth/token
       ▼
┌──────────────┐
│   AuthApi    │ (Retrofit)
│ .login(...)  │
└──────┬───────┘
       │ 3. TokenResponse(token)
       ▼
┌───────────────────┐
│ TokenProvider     │
│ .saveToken(ctx,   │ ◄─── Сохранение в SharedPreferences
│   token)          │      ("openway_prefs" / "user_token")
└───────────────────┘

        │
        │ Токен доступен для чтения
        │
        ▼
┌─────────────────────────────────────────────────┐
│         TokenProvider.getToken(context)         │
│  1. Читаем SharedPreferences                    │
│  2. Если null → fallback на DEMO_DRF_TOKEN      │
│     (только в BuildConfig.DEBUG)                │
└────┬────────────────────────────────┬───────────┘
     │                                 │
     │ HTTP Branch                     │ BLE Branch
     ▼                                 ▼
┌──────────────────┐         ┌────────────────┐
│ VerifyRepository │         │   BleClient    │
│ .verify(gateId,  │         │ .sendToken(    │
│   token)         │         │    token)      │
└────┬─────────────┘         └────┬───────────┘
     │                             │
     │ POST /api/v1/access/verify  │ Bluetooth GATT Write
     ▼                             ▼
┌──────────┐              ┌─────────────────┐
│VerifyApi │              │ ESP32 Device    │
│ .verify()│              │ (MAC: 00:4B:..) │
└──────────┘              └─────────────────┘

┌──────────────────────────────────────────────────┐
│              LOGOUT (Очистка токена)             │
│  MainActivity.exitAcc() → TokenProvider.         │
│  clearToken() → SharedPreferences.remove("user_  │
│  token") → navigate("loginScreen")               │
└──────────────────────────────────────────────────┘
```

---

## Источники кода (с путями и строками)

### 1. TokenProvider.kt
**Путь:** `app/src/main/java/com/example/openway/util/TokenProvider.kt`  
**Строки:** 1-33

**Ключевые контракты:**

#### 1.1 Константы хранилища (строки 7-8)
```kotlin
private const val PREFS = "openway_prefs"
private const val KEY = "user_token"
```

#### 1.2 Чтение токена (строки 10-16)
```kotlin
fun getToken(context: Context): String {
    val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    val saved = sp.getString(KEY, null)
    if (saved != null) return saved
    // Debug-only fallback; never ship demo token in release
    return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
}
```
- **Логика:** Сначала читает из SharedPreferences
- **Fallback (debug):** Возвращает `BuildConfig.DEMO_DRF_TOKEN` если токен не найден и `BuildConfig.DEBUG == true`
- **Fallback (release):** Возвращает пустую строку `""`

#### 1.3 Сохранение токена (строки 18-21)
```kotlin
fun saveToken(context: Context, token: String) {
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .edit().putString(KEY, token).apply()
}
```
- **Хранилище:** `SharedPreferences` с `MODE_PRIVATE`
- **⚠️ НЕ ЗАШИФРОВАНО:** Использует обычный SharedPreferences, НЕ EncryptedSharedPreferences

#### 1.4 Очистка токена (строки 23-27)
```kotlin
fun clearToken(context: Context) {
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .edit().remove(KEY).apply()
}
```

#### 1.5 Проверка наличия токена (строки 29-30)
```kotlin
fun hasToken(context: Context): Boolean = getToken(context).isNotBlank()
```

---

### 2. AuthRepository.kt
**Путь:** `app/src/main/java/com/example/openway/data/AuthRepository.kt`  
**Строки:** 1-18

#### 2.1 Login с сохранением токена (строки 9-14)
```kotlin
suspend fun login(context: Context, username: String, password: String): Result<String> =
    runCatching {
        val resp = api.login(LoginRequest(username, password))
        TokenProvider.saveToken(context, resp.token)  // ← СОХРАНЕНИЕ
        resp.token
    }
```
- **Вызывает:** `AuthApi.login()` → получает `TokenResponse(token: String)`
- **Сохраняет:** `TokenProvider.saveToken(context, resp.token)` — сразу после успешного ответа
- **Возвращает:** `Result<String>` (токен или ошибку)

---

### 3. AuthApi.kt
**Путь:** `app/src/main/java/com/example/openway/api/AuthApi.kt`  
**Строки:** 1-15

#### 3.1 Интерфейс API (строки 9-12)
```kotlin
interface AuthApi {
    @POST("/api/v1/auth/token")
    suspend fun login(@Body body: LoginRequest): TokenResponse
}
```

#### 3.2 DTO (строки 6-7)
```kotlin
data class LoginRequest(val username: String, val password: String)
data class TokenResponse(val token: String)
```

---

### 4. LoginScreen.kt (Вход пользователя)
**Путь:** `app/src/main/java/com/example/openway/LoginScreen.kt`  
**Строки:** 1-284

#### 4.1 Инициализация репозитория (строка 86)
```kotlin
val authRepo = remember { AuthRepository(ApiFactory.authApi) }
```

#### 4.2 Логика входа (строки 90-107)
```kotlin
fun submitLogin() {
    if (!canSubmit) return
    errorText = ""
    keyboardController?.hide()
    scope.launch {
        isLoading = true
        try {
            val res = authRepo.login(context, login, password)  // ← ВЫЗОВ
            res.onSuccess {
                navController.navigate("mainScreen")  // ← Переход после успеха
            }.onFailure { e ->
                errorText = humanizeNetworkError(e)  // ← Ошибка в UI
            }
        } finally {
            isLoading = false
        }
    }
}
```

#### 4.3 UI состояния (строки 80-81, 271-280)
```kotlin
var errorText by rememberSaveable { mutableStateOf("") }
var isLoading by rememberSaveable { mutableStateOf(false) }

// Кнопка входа:
Text(if (isLoading) "Входим…" else "Войти", fontSize = 16.sp)

// Отображение ошибок:
if (errorText.isNotBlank()) {
    Text(text = errorText, color = Color.Red, fontSize = 14.sp)
}
```

---

### 5. VerifyRepository.kt (HTTP-использование токена)
**Путь:** `app/src/main/java/com/example/openway/data/VerifyRepository.kt`  
**Строки:** 1-12

#### 5.1 Метод верификации (строки 7-8)
```kotlin
suspend fun verify(gateId: String, token: String) =
    runCatching { api.verify(VerifyRequest(gate_id = gateId, token = token)) }
```
- **Принимает токен как параметр** (НЕ читает сам)
- **Вызывающая сторона** должна передать `TokenProvider.getToken(context)`

---

### 6. VerifyApi.kt
**Путь:** `app/src/main/java/com/example/openway/api/VerifyApi.kt`  
**Строки:** 1-17

#### 6.1 Интерфейс API (строки 10-14)
```kotlin
interface VerifyApi {
    @Headers("Content-Type: application/json")
    @POST("/api/v1/access/verify")
    suspend fun verify(@Body body: VerifyRequest): VerifyResponse
}
```

#### 6.2 DTO (строки 7-8)
```kotlin
data class VerifyRequest(val gate_id: String, val token: String)
data class VerifyResponse(val decision: String, val reason: String, val duration_ms: Int? = null)
```
- **Токен передается в теле запроса** как поле `token`

---

### 7. MainActivity.kt (BLE-использование токена)
**Путь:** `app/src/main/java/com/example/openway/MainActivity.kt`  
**Строки:** 1-452

#### 7.1 Инициализация BleClient (строки 46, 51)
```kotlin
internal lateinit var bleClient: BleClient

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    bleClient = BleClient(this)
    // ...
}
```

#### 7.2 Получение токена для BLE (строки 59-61, 77-79)
```kotlin
fun sendTokenWithPerms(token: String? = null) {
    ensureBlePermsAndSend(token)
}

private fun ensureBlePermsAndSend(token: String? = null) {
    pendingToken = token ?: TokenProvider.getToken(this)  // ← ЧТЕНИЕ ТОКЕНА
    // ... проверка разрешений ...
}
```

#### 7.3 Отправка токена через BLE (строки 98-110)
```kotlin
private fun reallySendToken(token: String?) {
    if (token.isNullOrBlank()) {
        Toast.makeText(this, "Пустой токен", Toast.LENGTH_SHORT).show()
        Log.d(TAG, "empty token")
        return
    }
    Log.d(TAG, "sending token len=${token.length}")
    bleClient.sendToken(token) { ok, msg ->  // ← ВЫЗОВ BLE
        Log.d(TAG, "sendToken result ok=$ok, msg=$msg")
        Toast.makeText(this, if (ok) "Токен отправлен" else "Ошибка: $msg", Toast.LENGTH_SHORT)
            .show()
    }
}
```

#### 7.4 UI вызов BLE (строки 248-257)
```kotlin
BleButton(
    flagNfcButton = flagBleButton,
    flagTheme = flagTheme,
    onNfcButton = {
        flagBleButton = !flagBleButton
        if (flagBleButton) {
            act?.sendTokenWithPerms()  // ← Кнопка "Нажмите, чтобы пройти"
        }
    }
)
```

#### 7.5 Logout / Очистка токена (строки 425-436)
```kotlin
@Composable
fun exitAcc(navController: NavController) {
    val context = LocalContext.current
    
    Button(
        onClick = {
            TokenProvider.clearToken(context)  // ← ОЧИСТКА ТОКЕНА
            Toast.makeText(context, "Вы вышли", Toast.LENGTH_SHORT).show()
            navController.navigate("loginScreen") {
                popUpTo("mainScreen") { inclusive = true }
                launchSingleTop = true
            }
        },
        // ... UI ...
    ) {
        Row {
            Icon(painter = painterResource(id = R.drawable.exit), ...)
            Text("Выйти из аккаунта", color = Color.Red, fontSize = 16.sp)
        }
    }
}
```

#### 7.6 Закомментированный код verify (строки 164-207)
```kotlin
/*
Button(
    enabled = !isVerifying,
    onClick = {
        val token = TokenProvider.getToken(context)  // ← БЫЛО БЫ ЧТЕНИЕ
        if (token.isBlank()) {
            Toast.makeText(context, "Нет токена. Сначала войдите.", Toast.LENGTH_SHORT).show()
        } else {
            scope.launch {
                isVerifying = true
                try {
                    val result = verifyRepo.verify("front_door", token)
                    result.onSuccess { resp ->
                        Toast.makeText(context, "VERIFY: ${resp.decision}/${resp.reason}", ...).show()
                    }.onFailure { e ->
                        val errorMsg = humanizeNetworkError(e)
                        Toast.makeText(context, errorMsg, ...).show()
                    }
                } finally {
                    isVerifying = false
                }
            }
        }
    },
    ...
) { Text("Verify (front_door)") }
*/
```
- **⚠️ ЗАКОММЕНТИРОВАНО** — HTTP verify не активен в UI

---

### 8. BleClient.kt (BLE-отправка токена)
**Путь:** `app/src/main/java/com/example/openway/ble/BleClient.kt`  
**Строки:** 1-223

#### 8.1 Публичный API (строки 35-54)
```kotlin
fun sendToken(
    token: String,
    onResult: (Boolean, String) -> Unit = { _, _ -> }
) {
    scope.launch {
        val res = runCatching { sendTokenInternal(token) }
        withContext(Dispatchers.Main) {
            res.onSuccess { ok ->
                onResult(ok, if (!ok) "Подойдите ближе к устройству." else "")
            }.onFailure { e ->
                val errorMessage = when (e) {
                    is SecurityException -> "Отсутствуют разрешения для работы с Bluetooth..."
                    is IOException -> "Ошибка при подключении или передаче данных..."
                    else -> e.message ?: "Произошла неизвестная ошибка."
                }
                onResult(false, errorMessage)
            }
        }
    }
}
```

#### 8.2 Валидация токена (строки 76-77)
```kotlin
require(hasBlePermissions()) { "Нет разрешения на использования bluetooth" }
require(token.isNotEmpty()) { "Пустой токен" }
```

#### 8.3 Отправка через GATT (строки 135-150)
```kotlin
val data = token.toByteArray(Charsets.UTF_8)  // ← Конвертация в UTF-8
if (data.size > maxPayload) {
    Log.w(TAG, "token=${data.size} bytes > maxPayload=$maxPayload (нет увеличенного MTU)")
    cleanupGatt(); return@withLock false
}

ch.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT // с подтверждением
ch.value = data

if (!g.writeCharacteristic(ch)) {
    Log.w(TAG, "writeCharacteristic() returned false")
    cleanupGatt(); return@withLock false
}
val writeOk = withTimeoutOrNull(BleConfig.WRITE_TIMEOUT_MS) { state.writeComplete.await() } ?: false
Log.d(TAG, "writeOk=$writeOk")
```

---

### 9. ApiFactory.kt (Конфигурация HTTP)
**Путь:** `app/src/main/java/com/example/openway/api/ApiFactory.kt`  
**Строки:** 1-39

#### 9.1 Retrofit baseUrl (строки 28-29)
```kotlin
val retrofit: Retrofit = Retrofit.Builder()
    .baseUrl(BuildConfig.API_BASE_URL)  // ← Используется BuildConfig
    .client(client)
    .addConverterFactory(MoshiConverterFactory.create(moshi))
    .build()
```

#### 9.2 API инстансы (строки 34-35)
```kotlin
val authApi: AuthApi = retrofit.create(AuthApi::class.java)
val verifyApi: VerifyApi = retrofit.create(VerifyApi::class.java)
```

---

### 10. build.gradle.kts (BuildConfig)
**Путь:** `app/build.gradle.kts`  
**Строки:** 1-82

#### 10.1 BuildConfig включен (строки 47-50)
```kotlin
buildFeatures {
    compose = true
    buildConfig = true  // ← ВКЛЮЧЕН
}
```

#### 10.2 Debug buildType (строки 33-38)
```kotlin
debug {
    // LAN debug endpoint (replace <LAN_IP> with your host's LAN IP, e.g., 192.168.1.100)
    buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8001/\"")
    // Demo token ONLY in debug; do not ship in release
    buildConfigField("String", "DEMO_DRF_TOKEN", "\"edee5ecede95c8089112efe70a24b0d1fef5d3c4\"")
}
```
- **API_BASE_URL:** `http://10.0.2.2:8001/` (эмулятор localhost)
- **DEMO_DRF_TOKEN:** `edee5ecede95c8089112efe70a24b0d1fef5d3c4` (токен для отладки)

#### 10.3 Release buildType (строки 26-32)
```kotlin
release {
    isMinifyEnabled = false
    proguardFiles(
        getDefaultProguardFile("proguard-android-optimize.txt"),
        "proguard-rules.pro"
    )
}
```
- **⚠️ НЕТ `API_BASE_URL` и `DEMO_DRF_TOKEN` в release**
- **Следствие:** `BuildConfig.API_BASE_URL` и `BuildConfig.DEMO_DRF_TOKEN` **НЕ ОПРЕДЕЛЕНЫ** в release → **compile error** если используются

#### 10.4 Зависимость security-crypto (строки 62-63)
```kotlin
// Secure storage (if using EncryptedSharedPreferences)
implementation("androidx.security:security-crypto:1.1.0-alpha06")
```
- **⚠️ ОБЪЯВЛЕНА, НО НЕ ИСПОЛЬЗУЕТСЯ В КОДЕ**

---

## Фактический токен-флоу (пошаговая реконструкция)

### Шаг 1: Получение токена (Login)

**Триггер:** Пользователь нажимает кнопку "Войти" на `LoginScreen`

1. `LoginScreen.kt:260` — `Button(onClick = { submitLogin() })`
2. `LoginScreen.kt:94` — `authRepo.login(context, login, password)`
3. `AuthRepository.kt:11` — `api.login(LoginRequest(username, password))`
4. `AuthApi.kt:11` — `@POST("/api/v1/auth/token")` → **HTTP запрос к бэкенду**
5. **Ответ бэкенда:** `TokenResponse(token: "...")`
6. `AuthRepository.kt:12` — `TokenProvider.saveToken(context, resp.token)`
7. `TokenProvider.kt:18-21` — **Сохранение в SharedPreferences**  
   ```kotlin
   context.getSharedPreferences("openway_prefs", MODE_PRIVATE)
       .edit().putString("user_token", token).apply()
   ```
8. `LoginScreen.kt:99` — `navController.navigate("mainScreen")` — переход на главный экран

**Обработка ошибок:**
- `LoginScreen.kt:100-101` — `res.onFailure { e -> errorText = humanizeNetworkError(e) }`
- `ErrorText.kt:11-24` — Преобразование исключений в русские сообщения:
  - `SocketTimeoutException` → "Таймаут ожидания ответа"
  - `IOException` → "Нет соединения или сервер недоступен"
  - `HttpException` (400) → "Неверный логин или пароль"
  - `HttpException` (500-599) → "Сервер недоступен (ошибка XXX)"

---

### Шаг 2: Сохранение токена

**Где:** `TokenProvider.kt:18-21`  
**Хранилище:**
- **Имя файла SharedPreferences:** `"openway_prefs"`
- **Ключ:** `"user_token"`
- **Режим:** `Context.MODE_PRIVATE`
- **⚠️ Безопасность:** **PLAIN TEXT** — НЕ зашифровано, несмотря на наличие `security-crypto` в зависимостях

**Физическое расположение:**  
`/data/data/com.example.openway/shared_prefs/openway_prefs.xml`

---

### Шаг 3: Чтение токена

**Источник:** `TokenProvider.kt:10-16`

**Логика:**
```kotlin
fun getToken(context: Context): String {
    val sp = context.getSharedPreferences("openway_prefs", Context.MODE_PRIVATE)
    val saved = sp.getString("user_token", null)
    if (saved != null) return saved
    return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
}
```

**Места вызова:**

1. **MainActivity.kt:78** (BLE preparation)
   ```kotlin
   pendingToken = token ?: TokenProvider.getToken(this)
   ```

2. **MainActivity.kt:169** (закомментированный verify)
   ```kotlin
   val token = TokenProvider.getToken(context)
   ```

---

### Шаг 4A: Использование токена (HTTP Verify) — ЗАКОММЕНТИРОВАНО

**⚠️ ВАЖНО:** Функционал HTTP verify **ЗАКОММЕНТИРОВАН** в UI (MainActivity.kt:164-207)

**Если бы работало:**
1. `MainActivity.kt:169` — `val token = TokenProvider.getToken(context)`
2. `VerifyRepository.kt:7-8` — `api.verify(VerifyRequest(gate_id = "front_door", token = token))`
3. `VerifyApi.kt:13` — `@POST("/api/v1/access/verify")` → HTTP запрос с токеном в теле
4. **Ответ:** `VerifyResponse(decision: "ALLOW"/"DENY", reason: "...", duration_ms: ...)`
5. **UI:** Toast с `"VERIFY: ${resp.decision}/${resp.reason}"`

---

### Шаг 4B: Использование токена (BLE)

**Триггер:** Пользователь нажимает круглую кнопку "Нажмите, чтобы пройти"

1. `MainActivity.kt:252-256` — `BleButton.onNfcButton` → `act?.sendTokenWithPerms()`
2. `MainActivity.kt:59-61` — `sendTokenWithPerms()` → `ensureBlePermsAndSend()`
3. `MainActivity.kt:78` — `pendingToken = token ?: TokenProvider.getToken(this)` ← **ЧТЕНИЕ ТОКЕНА**
4. `MainActivity.kt:88-95` — Проверка Bluetooth permissions (SCAN/CONNECT/LOCATION)
5. `MainActivity.kt:104` — `bleClient.sendToken(token)` ← **ОТПРАВКА**
6. `BleClient.kt:39` — `sendTokenInternal(token)`:
   - Проверка `token.isNotEmpty()`
   - Подключение к `BleConfig.DEVICE_MAC` ("00:4B:12:F1:58:2E")
   - GATT service discovery
   - MTU negotiation (до 100 байт)
   - Запись токена в характеристику (`BleConfig.CHAR_UUID`)
7. `BleClient.kt:135-143` — Токен → UTF-8 bytes → GATT write
8. **Результат:** Toast "Токен отправлен" или "Ошибка: ..."

**BLE Configuration (BleConfig.kt:5-16):**
- **MAC:** `00:4B:12:F1:58:2E`
- **Service UUID:** `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
- **Characteristic UUID:** `beb5483e-36e1-4688-b7f5-ea07361b26a8`
- **Таймауты:** Connect=10s, Discover=7s, Write=5s

---

### Шаг 5: Очистка токена (Logout)

**Триггер:** Пользователь нажимает кнопку "Выйти из аккаунта"

1. `MainActivity.kt:428-436` — `exitAcc()` → `onClick`
2. `MainActivity.kt:430` — `TokenProvider.clearToken(context)` ← **ОЧИСТКА**
3. `TokenProvider.kt:24-27`:
   ```kotlin
   context.getSharedPreferences("openway_prefs", Context.MODE_PRIVATE)
       .edit().remove("user_token").apply()
   ```
4. `MainActivity.kt:431` — Toast: "Вы вышли"
5. `MainActivity.kt:432-435` — Навигация:
   ```kotlin
   navController.navigate("loginScreen") {
       popUpTo("mainScreen") { inclusive = true }  // ← Очистка back stack
       launchSingleTop = true
   }
   ```

---

## Фолбэки и окружения

### Debug режим

**BuildConfig (build.gradle.kts:33-38):**
```kotlin
debug {
    buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8001/\"")
    buildConfigField("String", "DEMO_DRF_TOKEN", "\"edee5ecede95c8089112efe70a24b0d1fef5d3c4\"")
}
```

**Поведение TokenProvider.getToken():**
```kotlin
if (saved != null) return saved
return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
```

**Сценарий использования DEMO_DRF_TOKEN:**
1. Пользователь НЕ выполнил login (токен отсутствует в SharedPreferences)
2. Приложение собрано в **debug** режиме
3. `TokenProvider.getToken()` возвращает `"edee5ecede95c8089112efe70a24b0d1fef5d3c4"`
4. **Этот токен может использоваться для BLE или HTTP запросов БЕЗ логина**

**⚠️ Риски:**
- В debug можно обойти экран логина и использовать demo-токен
- Если demo-токен валиден на бэкенде, это позволяет тестировать доступ без аутентификации

---

### Release режим

**BuildConfig (build.gradle.kts:26-32):**
```kotlin
release {
    isMinifyEnabled = false
    proguardFiles(...)
}
// ❌ НЕТ buildConfigField для API_BASE_URL и DEMO_DRF_TOKEN
```

**Следствия:**
1. `BuildConfig.API_BASE_URL` **НЕ ОПРЕДЕЛЁН** → **Compile Error** в `ApiFactory.kt:29`
2. `BuildConfig.DEMO_DRF_TOKEN` **НЕ ОПРЕДЕЛЁН** → **Compile Error** в `TokenProvider.kt:15`

**⚠️ КРИТИЧЕСКАЯ ПРОБЛЕМА:** **Приложение НЕ СОБИРАЕТСЯ в release режиме**

**Что должно быть (пример):**
```kotlin
release {
    buildConfigField("String", "API_BASE_URL", "\"https://api.production.com/\"")
    // DEMO_DRF_TOKEN НЕ ДОЛЖЕН БЫТЬ в release
}
```

**Поведение в release (если бы собиралось):**
```kotlin
// TokenProvider.kt:15
return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
//          ^^^^^^^^^^^^^^^^ = false in release
//                           ^^^^^^^^^^^^^^^^^^^^^^^ не определён → compile error
```

**Ожидаемое поведение (если исправить):**
- `BuildConfig.DEBUG == false` → возвращать пустую строку `""`
- `TokenProvider.hasToken()` → `false`
- **Пользователь должен войти через экран логина**

---

## Безопасность

### 🔴 Критические проблемы

#### 1. Токен НЕ зашифрован
**Проблема:**
- `TokenProvider.kt:18-21` использует **обычный SharedPreferences**
- **НЕ использует EncryptedSharedPreferences**, несмотря на наличие зависимости `security-crypto:1.1.0-alpha06`

**Файл на устройстве:**  
`/data/data/com.example.openway/shared_prefs/openway_prefs.xml`
```xml
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="user_token">eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...</string>
</map>
```

**Риски:**
- Токен читается в **plain text** при root-доступе
- Уязвим к **backup extraction** (ADB backup)
- Уязвим к **malware** с доступом к `/data/data`

**Рекомендация:**
```kotlin
// ДОЛЖНО БЫТЬ (но НЕ реализовано):
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()
    
val encryptedPrefs = EncryptedSharedPreferences.create(
    context,
    "openway_secure_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)
```

---

#### 2. Debug mode Network Security Config

**AndroidManifest.xml:**
- `app/src/debug/AndroidManifest.xml:3` — `android:networkSecurityConfig="@xml/network_security_config"`
- `app/src/debug/res/xml/network_security_config.xml:4` — `<base-config cleartextTrafficPermitted="true" />`

**Следствие:**
- В debug режиме разрешён **cleartext HTTP** (не HTTPS)
- `BuildConfig.API_BASE_URL = "http://10.0.2.2:8001/"` — **HTTP** (не HTTPS)

**Риски (только в debug):**
- Токен передаётся по **незашифрованному каналу**
- Уязвим к **MITM атакам** в локальной сети

**⚠️ НО:** В release этого файла нет → cleartext HTTP **запрещён** (Android default)

---

#### 3. Demo токен в debug

**DEMO_DRF_TOKEN:** `edee5ecede95c8089112efe70a24b0d1fef5d3c4`

**Где используется:**
- `TokenProvider.kt:15` — fallback если токен не найден и `BuildConfig.DEBUG == true`

**Риски:**
- Если этот токен валиден на **production бэкенде**, злоумышленник может:
  1. Собрать debug APK (или извлечь токен из BuildConfig)
  2. Использовать токен для доступа БЕЗ логина

**Рекомендация:**
- Demo-токен должен быть валиден **только на dev/staging окружении**
- Production бэкенд должен **отклонять** этот токен

---

#### 4. Release build НЕ компилируется

**Проблема:** `BuildConfig.API_BASE_URL` и `BuildConfig.DEMO_DRF_TOKEN` не определены в release

**Следствие:**
```
ApiFactory.kt:29: Unresolved reference: API_BASE_URL
TokenProvider.kt:15: Unresolved reference: DEMO_DRF_TOKEN
```

**Как исправить (НЕ ДЕЛАТЬ сейчас, только для справки):**
```kotlin
// build.gradle.kts
release {
    buildConfigField("String", "API_BASE_URL", "\"https://api.production.com/\"")
    // DEMO_DRF_TOKEN НЕ НУЖЕН в release
}

// TokenProvider.kt — условная компиляция:
return if (BuildConfig.DEBUG) {
    BuildConfig.DEMO_DRF_TOKEN  // Только в debug
} else {
    ""  // В release
}
```

---

## Гэп-анализ

### 1. Дублирование Context

**Проблема:**
- `TokenProvider` требует `Context` для каждого вызова
- `Context` передаётся из UI → Repository → TokenProvider

**Найдено:**
- `MainActivity.kt:78` — `TokenProvider.getToken(this)`
- `LoginScreen.kt:86` — `authRepo.login(context, login, password)`
- `AuthRepository.kt:9` — `login(context: Context, ...)`
- `MainActivity.kt:430` — `TokenProvider.clearToken(context)`

**Рекомендация (не реализовано):**
```kotlin
// DI с Hilt:
@Singleton
class TokenManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    fun getToken(): String = ...
}
```

---

### 2. EncryptedSharedPreferences не используется

**Зависимость объявлена:**
```kotlin
// app/build.gradle.kts:62-63
implementation("androidx.security:security-crypto:1.1.0-alpha06")
```

**Но НЕ используется в коде:**
```bash
$ grep -r "EncryptedSharedPreferences" app/src/main/
# (нет результатов)
```

**Следствие:** Зависимость **DEAD CODE** (неиспользуемая)

---

### 3. Verify функционал закомментирован

**Проблема:** HTTP verify (`/api/v1/access/verify`) **НЕ РАБОТАЕТ** в UI

**Код:**
- `MainActivity.kt:164-207` — весь блок `Button(onClick = { verify(...) })` закомментирован `/* ... */`

**Следствие:**
- `VerifyRepository` НЕ ИСПОЛЬЗУЕТСЯ
- `VerifyApi` НЕ ИСПОЛЬЗУЕТСЯ
- Единственный способ использовать токен — **BLE**

**⚠️ Вопрос:** Почему закомментировано? Недоработка или намеренно?

---

### 4. Отсутствие обработки ошибок в BLE

**LoginScreen:**
- ✅ Обработка HTTP ошибок: `humanizeNetworkError(e)` (ErrorText.kt:11-24)
- ✅ UI индикаторы: `isLoading`, `errorText`

**BLE (MainActivity.kt:98-110):**
- ⚠️ Обработка ошибок через `Toast` (не сохраняется в state)
- ⚠️ Нет UI индикатора загрузки для BLE
- ⚠️ Пользователь может кликнуть кнопку несколько раз (нет `isLoading` для BLE)

---

### 5. DEMO_DRF_TOKEN используется при пустом токене

**Логика:** `TokenProvider.kt:12-15`
```kotlin
val saved = sp.getString(KEY, null)
if (saved != null) return saved
return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
```

**Сценарии:**
1. **Первый запуск (debug)** → нет токена → возвращается `DEMO_DRF_TOKEN`
2. **После logout (debug)** → токен удалён → возвращается `DEMO_DRF_TOKEN`
3. **После logout (release)** → токен удалён → возвращается `""` (пустая строка)

**Проблема:**
- В debug пользователь может **обойти логин** и использовать BLE с DEMO токеном
- `hasToken()` вернёт `true` даже если пользователь не залогинен

**Рекомендация:**
- Добавить флаг `isLoggedIn` отдельно от токена
- Или запрещать использование DEMO токена в UI

---

### 6. Нет refresh token механики

**Проблема:**
- Токен сохраняется один раз после login
- **НЕТ механизма обновления токена** (refresh token)
- **НЕТ проверки валидности токена** (expiration)

**Следствие:**
- Если токен истекает → пользователь получит HTTP 401 на verify
- **НЕТ автоматического редиректа на логин** при истечении токена

---

### 7. Нет проверки успеха logout

**Проблема:** `MainActivity.kt:430-435`
```kotlin
TokenProvider.clearToken(context)  // Всегда успешна (void)
Toast.makeText(context, "Вы вышли", ...).show()
navController.navigate("loginScreen") { ... }
```

**Следствие:**
- Нельзя узнать, действительно ли токен удалён
- Нет проверки состояния после `clearToken()`

---

## Ручной тест-план (без запуска из Cursor)

### Сценарий 1: Успешный логин

**Preconditions:**
- Бэкенд запущен на `http://10.0.2.2:8001/` (эмулятор) или LAN IP (физ. устройство)
- Пользователь `andrey` существует с валидным паролем

**Шаги:**
1. Запустить debug APK
2. Ввести `andrey` / `(пароль)`
3. Нажать "Войти"

**Ожидаемый результат:**
- Кнопка меняется на "Входим…"
- Индикатор загрузки (CircularProgressIndicator)
- HTTP запрос: `POST http://10.0.2.2:8001/api/v1/auth/token`
- Ответ: `{"token": "..."}`
- Токен сохраняется в SharedPreferences (`openway_prefs` / `user_token`)
- Навигация на `MainScreen`
- Отображается "Андрей Арустамян" и "Генеральный директор"

**Проверка:**
```bash
# ADB shell на устройстве:
adb shell
run-as com.example.openway
cat /data/data/com.example.openway/shared_prefs/openway_prefs.xml
# Должен содержать <string name="user_token">...</string>
```

---

### Сценарий 2: Ошибка логина (неверный пароль)

**Шаги:**
1. Ввести `andrey` / `wrong_password`
2. Нажать "Войти"

**Ожидаемый результат:**
- HTTP запрос: `POST /api/v1/auth/token`
- Ответ: HTTP 400 Bad Request
- Текст ошибки (красный): "Неверный логин или пароль"
- Остаёмся на `LoginScreen`

---

### Сценарий 3: Ошибка сети (бэкенд недоступен)

**Preconditions:** Бэкенд выключен

**Шаги:**
1. Ввести любые credentials
2. Нажать "Войти"

**Ожидаемый результат:**
- HTTP таймаут или Connection refused
- Текст ошибки: "Нет соединения или сервер недоступен"

---

### Сценарий 4: BLE отправка токена (после логина)

**Preconditions:**
- Пользователь залогинен (токен сохранён)
- ESP32 включен с MAC `00:4B:12:F1:58:2E` и запущен GATT сервер

**Шаги:**
1. На `MainScreen` нажать круглую кнопку "Нажмите, чтобы пройти"
2. Предоставить Bluetooth permissions (если запрашивается)

**Ожидаемый результат:**
- `TokenProvider.getToken()` → возвращает сохранённый токен
- BLE подключение к `00:4B:12:F1:58:2E`
- GATT service discovery
- Запись токена в characteristic `beb5483e-36e1-4688-b7f5-ea07361b26a8`
- Toast: "Токен отправлен"
- Лог: `BleClient: writeOk=true`

**Проверка на ESP32:**
```cpp
// ESP32 должен получить токен в UTF-8
Serial.println(receivedToken);  // Должен совпадать с токеном из SharedPreferences
```

---

### Сценарий 5: BLE отправка токена (без логина, debug)

**Preconditions:**
- Пользователь **НЕ** залогинен (первый запуск)
- Debug build
- ESP32 включен

**Шаги:**
1. На `LoginScreen` закрыть приложение
2. Открыть приложение снова (или напрямую перейти на `MainScreen` если позволяет навигация)
3. Нажать BLE кнопку

**Ожидаемый результат:**
- `TokenProvider.getToken()` → SharedPreferences пустой → возвращает `BuildConfig.DEMO_DRF_TOKEN`
- BLE отправка токена `edee5ecede95c8089112efe70a24b0d1fef5d3c4`
- Toast: "Токен отправлен"

**⚠️ Риск:** Позволяет обходить логин в debug режиме

---

### Сценарий 6: Logout

**Preconditions:** Пользователь залогинен

**Шаги:**
1. На `MainScreen` прокрутить вниз
2. Нажать "Выйти из аккаунта" (красная кнопка)

**Ожидаемый результат:**
- `TokenProvider.clearToken()` → удаляется `user_token` из SharedPreferences
- Toast: "Вы вышли"
- Навигация на `LoginScreen`
- Back stack очищен (`popUpTo("mainScreen") { inclusive = true }`)

**Проверка:**
```bash
adb shell run-as com.example.openway
cat /data/data/com.example.openway/shared_prefs/openway_prefs.xml
# Должно быть: <map></map> (пустой)
```

---

### Сценарий 7: BLE ошибка (устройство не найдено)

**Preconditions:** ESP32 **ВЫКЛЮЧЕН**

**Шаги:**
1. Залогиниться
2. Нажать BLE кнопку

**Ожидаемый результат:**
- BLE подключение таймаут (10 секунд)
- Toast: "Подойдите ближе к устройству."
- Лог: `BleClient: connect timeout/fail`

---

### Сценарий 8: Verify (HTTP) — НЕ РАБОТАЕТ

**Статус:** ⚠️ Функционал закомментирован (`MainActivity.kt:164-207`)

**Если бы работал:**
1. Залогиниться
2. Нажать кнопку "Verify (front_door)"
3. `TokenProvider.getToken()` → токен
4. HTTP: `POST /api/v1/access/verify` с `{"gate_id": "front_door", "token": "..."}`
5. Ответ: `{"decision": "ALLOW", "reason": "...", "duration_ms": ...}`
6. Toast: "VERIFY: ALLOW/..."

**Текущее поведение:** Кнопка отсутствует в UI

---

## Резюме

### ✅ Что работает

1. **Login flow:** LoginScreen → AuthRepository → AuthApi → saveToken ✅
2. **Token storage:** SharedPreferences (plain text) ✅
3. **Token retrieval:** getToken() с fallback на DEMO_DRF_TOKEN (debug) ✅
4. **BLE token transmission:** MainActivity → BleClient → GATT write ✅
5. **Logout:** clearToken() + навигация на LoginScreen ✅
6. **Error handling:** humanizeNetworkError() для HTTP ошибок ✅

---

### 🔴 Критические проблемы

1. **Токен НЕ зашифрован** — plain SharedPreferences вместо EncryptedSharedPreferences
2. **Release build НЕ компилируется** — отсутствуют API_BASE_URL и DEMO_DRF_TOKEN в release buildType
3. **HTTP Verify закомментирован** — VerifyRepository/VerifyApi не используются
4. **security-crypto зависимость не используется** — dead code

---

### 🟡 Средние проблемы

5. **DEMO токен доступен после logout** — в debug возвращается DEMO_DRF_TOKEN при пустом SharedPreferences
6. **Нет проверки валидности токена** — токен может истечь, но приложение не обрабатывает 401
7. **Cleartext HTTP в debug** — токен передаётся незашифрованно (MITM риск)
8. **Нет refresh token** — токен не обновляется автоматически

---

### 🟢 Архитектурные улучшения

9. **Context передаётся через все слои** — нужен DI (Hilt)
10. **Нет централизованного error handling** — каждый экран обрабатывает ошибки по-своему
11. **BLE нет loading state** — пользователь не видит процесс отправки
12. **hasToken() неинформативен** — не различает "залогинен" и "есть DEMO токен"

---

## Пути к файлам (Quick Reference)

| Компонент | Путь | Строки |
|-----------|------|--------|
| **TokenProvider** | `app/src/main/java/com/example/openway/util/TokenProvider.kt` | 1-33 |
| **AuthRepository** | `app/src/main/java/com/example/openway/data/AuthRepository.kt` | 1-18 |
| **AuthApi** | `app/src/main/java/com/example/openway/api/AuthApi.kt` | 1-15 |
| **VerifyRepository** | `app/src/main/java/com/example/openway/data/VerifyRepository.kt` | 1-12 |
| **VerifyApi** | `app/src/main/java/com/example/openway/api/VerifyApi.kt` | 1-17 |
| **LoginScreen** | `app/src/main/java/com/example/openway/LoginScreen.kt` | 1-284 |
| **MainActivity** | `app/src/main/java/com/example/openway/MainActivity.kt` | 1-452 |
| **BleClient** | `app/src/main/java/com/example/openway/ble/BleClient.kt` | 1-223 |
| **BleConfig** | `app/src/main/java/com/example/openway/ble/BleConfig.kt` | 1-17 |
| **ApiFactory** | `app/src/main/java/com/example/openway/api/ApiFactory.kt` | 1-39 |
| **ErrorText** | `app/src/main/java/com/example/openway/util/ErrorText.kt` | 1-26 |
| **build.gradle.kts** | `app/build.gradle.kts` | 1-82 |

---

## Места использования TokenProvider (все вхождения)

```bash
# TokenProvider.saveToken()
app/src/main/java/com/example/openway/data/AuthRepository.kt:12

# TokenProvider.getToken()
app/src/main/java/com/example/openway/MainActivity.kt:78
app/src/main/java/com/example/openway/MainActivity.kt:169  # (закомментировано)

# TokenProvider.clearToken()
app/src/main/java/com/example/openway/MainActivity.kt:430
```

---

## BuildConfig.DEMO_DRF_TOKEN (все вхождения)

```bash
# Объявление:
app/build.gradle.kts:37
    buildConfigField("String", "DEMO_DRF_TOKEN", "\"edee5ecede95c8089112efe70a24b0d1fef5d3c4\"")

# Использование:
app/src/main/java/com/example/openway/util/TokenProvider.kt:15
    return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
```

---

**Конец отчёта**  
**Автор:** Token Flow Auditor  
**Версия:** 1.0  
**Дата:** 2025-10-18

