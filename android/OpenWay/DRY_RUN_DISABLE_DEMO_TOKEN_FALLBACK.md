# 🔍 DRY-RUN: Disable Debug DEMO Token Fallback

**Дата:** 2025-10-18  
**Цель:** Отключить автоматический fallback на `BuildConfig.DEMO_DRF_TOKEN` в `TokenProvider.getToken()`  
**Статус:** ✅ **ПРИМЕНЕНО** — Minimal Patch успешно применён

---

## Step 1: Read-Only Audit ✅

### Текущая логика TokenProvider

**Файл:** `app/src/main/java/com/example/openway/util/TokenProvider.kt`  
**Строки:** 1-33

#### Константы (строки 7-8)
```kotlin
private const val PREFS = "openway_prefs"
private const val KEY = "user_token"
```

#### getToken() — ТЕКУЩАЯ ЛОГИКА (строки 10-16)
```kotlin
fun getToken(context: Context): String {
    val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    val saved = sp.getString(KEY, null)
    if (saved != null) return saved
    // Debug-only fallback; never ship demo token in release
    return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
}
```

**Проблема:**
- На первом запуске (debug) → `saved == null` → возвращается `DEMO_DRF_TOKEN`
- После logout (debug) → `saved == null` → возвращается `DEMO_DRF_TOKEN`
- Пользователь может обойти экран логина и использовать BLE с demo токеном

---

### Места использования BuildConfig.DEMO_DRF_TOKEN

**Поиск:** `grep -r "BuildConfig.DEMO_DRF_TOKEN" app/src/main/`

**Результаты:**
```
app/src/main/java/com/example/openway/util/TokenProvider.kt:15
    return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
```

✅ **Используется ТОЛЬКО в TokenProvider.kt:15** — других мест НЕТ

---

### Места вызова TokenProvider.getToken()

**Поиск:** `grep -r "TokenProvider.getToken" app/src/main/`

**Результаты:**

#### 1. MainActivity.kt:78 (BLE path) — АКТИВЕН
```kotlin
private fun ensureBlePermsAndSend(token: String? = null) {
    pendingToken = token ?: TokenProvider.getToken(this)  // ← ЧТЕНИЕ
    // ... permissions check ...
}
```

#### 2. MainActivity.kt:169 (HTTP verify) — ЗАКОММЕНТИРОВАН
```kotlin
/*
onClick = {
    val token = TokenProvider.getToken(context)  // ← ЧТЕНИЕ
    if (token.isBlank()) {
        Toast.makeText(context, "Нет токена. Сначала войдите.", ...).show()
    } else {
        // ... verify logic ...
    }
}
*/
```

**Итого:** 1 активное использование (BLE), 1 закомментированное (verify)

---

### Места вызова TokenProvider.hasToken()

**Поиск:** `grep -r "TokenProvider.hasToken" app/src/main/`

**Результаты:** ❌ НЕ ИСПОЛЬЗУЕТСЯ в коде (метод определён, но не вызывается)

---

### Другие методы TokenProvider

#### saveToken() — используется в AuthRepository.kt:12
```kotlin
val resp = api.login(LoginRequest(username, password))
TokenProvider.saveToken(context, resp.token)  // ← СОХРАНЕНИЕ
```

#### clearToken() — используется в MainActivity.kt:430
```kotlin
onClick = {
    TokenProvider.clearToken(context)  // ← ОЧИСТКА
    Toast.makeText(context, "Вы вышли", ...).show()
    navController.navigate("loginScreen") { ... }
}
```

---

## Step 2: PROPOSED PATCH (Minimal) ⏸️

### Патч — Отключение DEMO fallback

**Файл:** `app/src/main/java/com/example/openway/util/TokenProvider.kt`

```diff
--- a/app/src/main/java/com/example/openway/util/TokenProvider.kt
+++ b/app/src/main/java/com/example/openway/util/TokenProvider.kt
@@ -1,7 +1,6 @@
 package com.example.openway.util
 
 import android.content.Context
-import com.example.openway.BuildConfig
 
 object TokenProvider {
     private const val PREFS = "openway_prefs"
@@ -9,12 +8,14 @@ object TokenProvider {
 
+    /**
+     * Returns the stored auth token or empty string if none.
+     * No debug fallback — empty means "not logged in".
+     */
     fun getToken(context: Context): String {
         val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
-        val saved = sp.getString(KEY, null)
-        if (saved != null) return saved
-        // Debug-only fallback; never ship demo token in release
-        return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
+        return sp.getString(KEY, "") ?: ""
     }
 
     fun saveToken(context: Context, token: String) {
@@ -27,7 +28,12 @@ object TokenProvider {
             .edit().remove(KEY).apply()
     }
 
-    fun hasToken(context: Context): Boolean = getToken(context).isNotBlank()
+    /** True only when a real token is stored in prefs. */
+    fun hasToken(context: Context): Boolean {
+        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
+        val saved = sp.getString(KEY, null)
+        return !saved.isNullOrBlank()
+    }
 }
```

### Изменения в Minimal патче:

1. **Удалён import BuildConfig** (строка 4) — больше не нужен
2. **getToken() упрощён** (строки 10-16):
   - Убрана логика fallback на `DEMO_DRF_TOKEN`
   - Теперь просто возвращает `sp.getString(KEY, "") ?: ""`
   - Если токена нет → вернёт `""`
3. **hasToken() улучшен** (строки 29-33):
   - Теперь читает prefs напрямую (не через `getToken()`)
   - Избегает confusion с возвращаемым значением
   - Проверяет `!saved.isNullOrBlank()`
4. **Добавлены комментарии** для ясности

---

## Step 3: OPTIONAL PATCH (Dev Flag) ⏸️

### Патч — Управляемый DEMO fallback (если попросят)

**Файл:** `app/src/main/java/com/example/openway/util/TokenProvider.kt`

```diff
--- a/app/src/main/java/com/example/openway/util/TokenProvider.kt
+++ b/app/src/main/java/com/example/openway/util/TokenProvider.kt
@@ -1,17 +1,20 @@
 package com.example.openway.util
 
 import android.content.Context
+import com.example.openway.BuildConfig
 
 object TokenProvider {
     private const val PREFS = "openway_prefs"
     private const val KEY = "user_token"
+    private const val KEY_DEMO_FALLBACK = "use_demo_token"
 
+    /**
+     * Returns stored token or empty. 
+     * In DEBUG: returns DEMO token ONLY if enableDemoFallback(true) was called.
+     */
     fun getToken(context: Context): String {
         val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
-        val saved = sp.getString(KEY, null)
-        if (saved != null) return saved
-        // Debug-only fallback; never ship demo token in release
-        return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
+        val saved = sp.getString(KEY, null)
+        if (!saved.isNullOrBlank()) return saved
+        // Fallback only if explicitly enabled (default: false)
+        val useDemo = sp.getBoolean(KEY_DEMO_FALLBACK, false)
+        return if (useDemo && BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
     }
 
     fun saveToken(context: Context, token: String) {
@@ -24,7 +27,22 @@ object TokenProvider {
             .edit().remove(KEY).apply()
     }
 
-    fun hasToken(context: Context): Boolean = getToken(context).isNotBlank()
+    /** True only when a real token is stored in prefs. */
+    fun hasToken(context: Context): Boolean {
+        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
+        val saved = sp.getString(KEY, null)
+        return !saved.isNullOrBlank()
+    }
+
+    /** Enable/disable DEMO token fallback (debug-only, default: false). */
+    fun enableDemoFallback(context: Context, enabled: Boolean) {
+        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
+            .edit().putBoolean(KEY_DEMO_FALLBACK, enabled).apply()
+    }
+
+    /** Check if DEMO token fallback is enabled. */
+    fun isDemoFallbackEnabled(context: Context): Boolean {
+        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
+        return sp.getBoolean(KEY_DEMO_FALLBACK, false)
+    }
 }
```

### Изменения в Optional патче:

1. **Сохранён import BuildConfig** — нужен для DEMO_DRF_TOKEN
2. **Добавлена константа KEY_DEMO_FALLBACK** (строка 9) — флаг в SharedPreferences
3. **getToken() с условным fallback** (строки 10-20):
   - Читает флаг `use_demo_token` из prefs
   - DEMO токен возвращается **только если флаг = true И BuildConfig.DEBUG**
   - **По умолчанию флаг = false** → fallback НЕ работает
4. **Добавлены методы управления** (строки 36-45):
   - `enableDemoFallback(context, enabled)` — включить/выключить
   - `isDemoFallbackEnabled(context)` — проверить статус
5. **hasToken() улучшен** (как в Minimal патче)

**Применение (если одобрят Optional):**
```kotlin
// В debug меню или экране настроек:
TokenProvider.enableDemoFallback(context, true)  // Включить DEMO токен
// Теперь getToken() вернёт DEMO токен при отсутствии сохранённого

TokenProvider.enableDemoFallback(context, false) // Выключить (вернуть к норме)
```

---

## Step 4: Impact Analysis 🔍

### Изменения в поведении после применения MINIMAL патча

#### Сценарий 1: Первый запуск (debug, без логина)

**ДО патча:**
```kotlin
TokenProvider.getToken(context)  // → "edee5ecede95c8089112efe70a24b0d1fef5d3c4"
TokenProvider.hasToken(context)  // → true (!)
```
- BLE отправка работает с DEMO токеном
- Пользователь может обойти логин

**ПОСЛЕ патча:**
```kotlin
TokenProvider.getToken(context)  // → ""
TokenProvider.hasToken(context)  // → false
```
- BLE отправка: `MainActivity.kt:99` → "Пустой токен" (toast)
- HTTP verify (если раскомментировать): `MainActivity.kt:170` → "Нет токена. Сначала войдите."

---

#### Сценарий 2: После logout (debug)

**ДО патча:**
```kotlin
TokenProvider.clearToken(context)  // Удаляет user_token из prefs
TokenProvider.getToken(context)    // → "edee5ecede95c8089112efe70a24b0d1fef5d3c4"
```
- После выхода DEMO токен всё ещё доступен
- Можно использовать BLE без повторного логина

**ПОСЛЕ патча:**
```kotlin
TokenProvider.clearToken(context)  // Удаляет user_token из prefs
TokenProvider.getToken(context)    // → ""
```
- После выхода токен пустой
- Требуется повторный логин для BLE/verify

---

#### Сценарий 3: После успешного логина

**ДО и ПОСЛЕ патча — БЕЗ ИЗМЕНЕНИЙ:**
```kotlin
authRepo.login(context, "andrey", "password")
// → saveToken(context, "abc123...")
TokenProvider.getToken(context)  // → "abc123..."
```
- Сохранённый токен работает как обычно
- **Нет изменений в основном флоу**

---

#### Сценарий 4: Release build

**ДО патча:**
```kotlin
// BuildConfig.DEMO_DRF_TOKEN не определён в release
// → Compile error
```

**ПОСЛЕ Minimal патча:**
```kotlin
// BuildConfig больше не используется в TokenProvider
// → Release build КОМПИЛИРУЕТСЯ (если API_BASE_URL тоже добавлен)
```

**⚠️ ВАЖНО:** Release build всё ещё не компилируется из-за:
- `ApiFactory.kt:29` использует `BuildConfig.API_BASE_URL` (не определён в release)

**Нужно отдельно добавить в build.gradle.kts:**
```kotlin
release {
    buildConfigField("String", "API_BASE_URL", "\"https://api.production.com/\"")
    // DEMO_DRF_TOKEN НЕ нужен в release
}
```

---

### Проверка всех call sites

#### 1. MainActivity.kt:78 (BLE path) — ✅ Корректно

**ДО патча:**
```kotlin
pendingToken = token ?: TokenProvider.getToken(this)
// token == null → getToken() → "DEMO_..." или saved token

reallySendToken(pendingToken) {
    if (token.isNullOrBlank()) {
        Toast.makeText(this, "Пустой токен", ...).show()
        return
    }
    bleClient.sendToken(token) { ... }
}
```
- Если getToken() вернёт DEMO токен → BLE отправка работает

**ПОСЛЕ патча:**
```kotlin
pendingToken = token ?: TokenProvider.getToken(this)
// token == null → getToken() → "" (если не залогинен)

reallySendToken(pendingToken) {
    if (token.isNullOrBlank()) {
        Toast.makeText(this, "Пустой токен", ...).show()  // ← СЮДА
        return  // BLE не отправляется
    }
}
```
- ✅ **Поведение корректно:** Пустой токен → toast "Пустой токен" → BLE не отправляется
- ✅ **Требуется логин** для работы BLE

---

#### 2. MainActivity.kt:169 (verify) — ✅ Корректно (закомментирован)

**ДО патча:**
```kotlin
val token = TokenProvider.getToken(context)
if (token.isBlank()) {
    Toast.makeText(context, "Нет токена. Сначала войдите.", ...).show()
} else {
    verifyRepo.verify("front_door", token)
}
```
- Если getToken() вернёт DEMO токен → verify выполнится

**ПОСЛЕ патча:**
```kotlin
val token = TokenProvider.getToken(context)  // → ""
if (token.isBlank()) {  // ← TRUE
    Toast.makeText(context, "Нет токена. Сначала войдите.", ...).show()
}
```
- ✅ **Поведение корректно:** Покажет toast "Нет токена. Сначала войдите."

---

#### 3. hasToken() — улучшен

**ДО патча:**
```kotlin
fun hasToken(context: Context): Boolean = getToken(context).isNotBlank()
```
- Вызывает getToken() → может вернуть DEMO токен → `hasToken() == true` (неправильно)

**ПОСЛЕ патча:**
```kotlin
fun hasToken(context: Context): Boolean {
    val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    val saved = sp.getString(KEY, null)
    return !saved.isNullOrBlank()
}
```
- ✅ **Читает prefs напрямую** → проверяет РЕАЛЬНОЕ наличие токена
- ✅ **Не зависит от getToken()** → нет confusion с fallback логикой

---

## Step 5: Testing Guide (Manual) 📋

### Тест 1: Первый запуск без логина (debug)

**Preconditions:**
- Debug APK установлен
- Первый запуск (нет сохранённого токена)

**Шаги:**
1. Открыть приложение → появляется `LoginScreen`
2. **НЕ ВХОДИТЬ**, вместо этого попытаться перейти на `MainScreen` (если возможно через навигацию)
3. Нажать круглую BLE кнопку

**Ожидаемый результат ПОСЛЕ патча:**
- `TokenProvider.getToken()` → `""`
- `MainActivity.kt:99` → Toast: **"Пустой токен"**
- BLE НЕ отправляется
- ✅ **Требуется логин**

**Ожидаемый результат ДО патча (текущее поведение):**
- `TokenProvider.getToken()` → `"edee5ecede95c8089112efe70a24b0d1fef5d3c4"`
- BLE отправка с DEMO токеном
- ❌ **Логин не требуется** (обход безопасности)

---

### Тест 2: После logout (debug)

**Preconditions:**
- Пользователь залогинен
- Токен сохранён в SharedPreferences

**Шаги:**
1. На `MainScreen` нажать "Выйти из аккаунта"
2. `TokenProvider.clearToken()` вызван
3. Вернуться на `MainScreen` (или остаться, если навигация не форсирует logout)
4. Нажать BLE кнопку

**Ожидаемый результат ПОСЛЕ патча:**
- Toast: **"Пустой токен"**
- BLE не отправляется
- ✅ **Требуется повторный логин**

**Ожидаемый результат ДО патча:**
- BLE отправка с DEMO токеном
- ❌ **Logout не эффективен** (можно продолжить использовать приложение)

---

### Тест 3: Успешный логин → BLE (debug и release)

**Шаги:**
1. Ввести `andrey` / `(valid password)`
2. Нажать "Войти"
3. Переход на `MainScreen`
4. Нажать BLE кнопку

**Ожидаемый результат ПОСЛЕ патча:**
- `TokenProvider.getToken()` → `"реальный_токен_от_бэкенда"`
- BLE отправка работает
- ✅ **БЕЗ ИЗМЕНЕНИЙ** — основной флоу не затронут

---

### Тест 4: HTTP Verify (если раскомментировать)

**Preconditions:** Раскомментировать `MainActivity.kt:164-207`

**Шаги (без логина):**
1. Нажать кнопку "Verify (front_door)"

**Ожидаемый результат ПОСЛЕ патча:**
- `TokenProvider.getToken()` → `""`
- `if (token.isBlank())` → **true**
- Toast: **"Нет токена. Сначала войдите."**
- HTTP запрос НЕ отправляется
- ✅ **Корректное поведение**

**Ожидаемый результат ДО патча:**
- `TokenProvider.getToken()` → `"edee5ecede95c8089112efe70a24b0d1fef5d3c4"`
- HTTP verify выполняется с DEMO токеном
- ❌ **Обход логина**

---

### Тест 5: hasToken() проверка

**Шаги:**
1. Без логина: `TokenProvider.hasToken(context)`
2. После логина: `TokenProvider.hasToken(context)`
3. После logout: `TokenProvider.hasToken(context)`

**Ожидаемые результаты ПОСЛЕ патча:**
1. Без логина: `false` ✅
2. После логина: `true` ✅
3. После logout: `false` ✅

**Результаты ДО патча:**
1. Без логина (debug): `true` ❌ (из-за DEMO токена)
2. После логина: `true` ✅
3. После logout (debug): `true` ❌ (из-за DEMO токена)

---

### Тест 6: Optional Flag (если одобрят Optional патч)

**Preconditions:** Optional патч применён

**Шаги:**
1. Первый запуск (без логина)
2. `TokenProvider.getToken(context)` → `""` (по умолчанию)
3. В debug меню вызвать: `TokenProvider.enableDemoFallback(context, true)`
4. `TokenProvider.getToken(context)` → `"edee5ecede95c8089112efe70a24b0d1fef5d3c4"`
5. BLE отправка работает с DEMO токеном
6. Вызвать: `TokenProvider.enableDemoFallback(context, false)`
7. `TokenProvider.getToken(context)` → `""`

**Польза:**
- ✅ Контролируемый доступ к DEMO токену для тестирования
- ✅ По умолчанию выключен → безопасно
- ✅ Можно включить через debug UI (например, секретный 5x tap на лого)

---

## Comparison: Minimal vs Optional Патч

| Критерий | Minimal | Optional (Dev Flag) |
|----------|---------|---------------------|
| **Безопасность по умолчанию** | ✅ DEMO токен НИКОГДА не используется | ✅ DEMO токен выключен по умолчанию |
| **Удобство тестирования** | ❌ Нужно логиниться каждый раз | ✅ Можно включить DEMO для быстрого теста |
| **Сложность кода** | ✅ Простой (4 строки) | ⚠️ Средняя (+3 метода, +1 константа) |
| **Риск утечки DEMO** | ✅ Минимальный (токен не используется) | ⚠️ Низкий (нужно явно включить флаг) |
| **Release build** | ✅ Компилируется (нет BuildConfig) | ✅ Компилируется (BuildConfig.DEBUG=false) |
| **Обратная совместимость** | ✅ Все call sites работают | ✅ Все call sites работают |

---

## Рекомендации 💡

### Выбор патча

**Minimal патч — рекомендуется для:**
- Production-ready приложения
- Строгий security policy
- Простота кода важнее удобства разработки

**Optional патч — рекомендуется для:**
- Активная разработка с частыми тестами
- Нужен быстрый доступ к функциям без логина
- Есть debug UI для управления флагом

---

### После применения патча

#### 1. Обновить ANDROID_TOKEN_FLOW_AUDIT.md

**Секция "Фолбэки и окружения" → Debug режим:**
```markdown
**Поведение TokenProvider.getToken() (ПОСЛЕ ПАТЧА):**
```kotlin
// Minimal патч:
val saved = sp.getString(KEY, null)
return sp.getString(KEY, "") ?: ""  // Всегда "" если нет токена

// Optional патч:
val useDemo = sp.getBoolean(KEY_DEMO_FALLBACK, false)
return if (useDemo && BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
// По умолчанию useDemo = false → нет fallback
```

**Сценарий использования DEMO_DRF_TOKEN:**
- **Minimal:** ❌ НИКОГДА (токен не используется автоматически)
- **Optional:** ⚠️ Только если вызван `enableDemoFallback(context, true)` (по умолчанию выключен)
```

#### 2. Добавить debug UI (только для Optional патча)

**Пример: Секретная команда на LoginScreen:**
```kotlin
// LoginScreen.kt
var tapCount by remember { mutableStateOf(0) }
val isDemoEnabled = remember { TokenProvider.isDemoFallbackEnabled(context) }

Text(
    text = "Добро пожаловать",
    fontSize = 22.sp,
    color = Color.Black,
    modifier = Modifier.clickable {
        tapCount++
        if (tapCount >= 5) {
            tapCount = 0
            val newState = !isDemoEnabled
            TokenProvider.enableDemoFallback(context, newState)
            Toast.makeText(
                context, 
                "DEMO fallback: ${if (newState) "ON" else "OFF"}", 
                Toast.LENGTH_SHORT
            ).show()
        }
    }
)
```

---

#### 3. Исправить release build (НЕ ЧАСТЬ ЭТОГО ПАТЧА)

**Проблема:** `ApiFactory.kt:29` → `BuildConfig.API_BASE_URL` не определён в release

**Отдельный патч (не применять сейчас):**
```kotlin
// app/build.gradle.kts
release {
    isMinifyEnabled = false
    proguardFiles(...)
    buildConfigField("String", "API_BASE_URL", "\"https://api.production.com/\"")
}
```

---

## Дополнительная проверка: Нет других ссылок на DEMO_DRF_TOKEN

**Поиск по всему проекту:**
```bash
grep -r "DEMO_DRF_TOKEN" android/OpenWay/app/src/main/
```

**Результат:**
```
app/src/main/java/com/example/openway/util/TokenProvider.kt:15
    return if (BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
```

✅ **Подтверждено:** Единственное использование в коде — `TokenProvider.kt:15`

**Поиск в build.gradle.kts:**
```bash
grep -r "DEMO_DRF_TOKEN" android/OpenWay/app/build.gradle.kts
```

**Результат:**
```
app/build.gradle.kts:37
    buildConfigField("String", "DEMO_DRF_TOKEN", "\"edee5ecede95c8089112efe70a24b0d1fef5d3c4\"")
```

✅ **Подтверждено:** Объявление в debug buildType

---

## Риски и митигации 🛡️

### Риск 1: Команда привыкла к DEMO токену для тестов

**Проблема:** Разработчики могут быть разочарованы, если каждый раз нужно логиниться

**Митигация:**
- **Minimal:** Добавить валидного пользователя `test`/`test` на dev бэкенде
- **Optional:** Использовать `enableDemoFallback(context, true)` в debug меню

---

### Риск 2: Забыли про DEMO токен в build.gradle.kts

**Проблема:** После Minimal патча `buildConfigField("String", "DEMO_DRF_TOKEN", ...)` остаётся в build.gradle.kts, но не используется

**Митигация:**
- ✅ Это НЕ проблема: BuildConfig поле будет определено, но просто не используется в коде
- ⚠️ Можно удалить из build.gradle.kts:37 в будущем (отдельный патч)

---

### Риск 3: Сломается release build

**Проблема:** Даже после Minimal патча release build НЕ компилируется из-за `BuildConfig.API_BASE_URL`

**Митигация:**
- ⚠️ Это **ОТДЕЛЬНАЯ ПРОБЛЕМА** (не часть этого патча)
- Решение: Добавить `API_BASE_URL` в release buildType (см. выше)

---

## Unified Diffs (Ready to Apply)

### ВАРИАНТ A: Minimal Patch (Рекомендуется)

**Команда для применения (НЕ ВЫПОЛНЯТЬ сейчас):**
```bash
# search_replace tool в Cursor:
# file: app/src/main/java/com/example/openway/util/TokenProvider.kt
# old_string: (весь файл с старой логикой)
# new_string: (весь файл с новой логикой)
```

**Полный файл ПОСЛЕ Minimal патча:**
```kotlin
package com.example.openway.util

import android.content.Context

object TokenProvider {
    private const val PREFS = "openway_prefs"
    private const val KEY = "user_token"

    /**
     * Returns the stored auth token or empty string if none.
     * No debug fallback — empty means "not logged in".
     */
    fun getToken(context: Context): String {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return sp.getString(KEY, "") ?: ""
    }

    fun saveToken(context: Context, token: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, token).apply()
    }

    /** Clears stored auth token. Used on logout. */
    fun clearToken(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(KEY).apply()
    }

    /** True only when a real token is stored in prefs. */
    fun hasToken(context: Context): Boolean {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = sp.getString(KEY, null)
        return !saved.isNullOrBlank()
    }
}
```

**Изменённые строки:**
- 1-4: Удалён `import com.example.openway.BuildConfig`
- 10-16: Новая логика `getToken()` без fallback
- 29-33: Новая логика `hasToken()` с прямым чтением prefs

---

### ВАРИАНТ B: Optional Dev-Flag Patch (Если попросят)

**Полный файл ПОСЛЕ Optional патча:**
```kotlin
package com.example.openway.util

import android.content.Context
import com.example.openway.BuildConfig

object TokenProvider {
    private const val PREFS = "openway_prefs"
    private const val KEY = "user_token"
    private const val KEY_DEMO_FALLBACK = "use_demo_token"

    /**
     * Returns stored token or empty. 
     * In DEBUG: returns DEMO token ONLY if enableDemoFallback(true) was called.
     */
    fun getToken(context: Context): String {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = sp.getString(KEY, null)
        if (!saved.isNullOrBlank()) return saved
        // Fallback only if explicitly enabled (default: false)
        val useDemo = sp.getBoolean(KEY_DEMO_FALLBACK, false)
        return if (useDemo && BuildConfig.DEBUG) BuildConfig.DEMO_DRF_TOKEN else ""
    }

    fun saveToken(context: Context, token: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, token).apply()
    }

    /** Clears stored auth token. Used on logout. */
    fun clearToken(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(KEY).apply()
    }

    /** True only when a real token is stored in prefs. */
    fun hasToken(context: Context): Boolean {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val saved = sp.getString(KEY, null)
        return !saved.isNullOrBlank()
    }

    /** Enable/disable DEMO token fallback (debug-only, default: false). */
    fun enableDemoFallback(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_DEMO_FALLBACK, enabled).apply()
    }

    /** Check if DEMO token fallback is enabled. */
    fun isDemoFallbackEnabled(context: Context): Boolean {
        val sp = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return sp.getBoolean(KEY_DEMO_FALLBACK, false)
    }
}
```

**Изменённые строки:**
- 9: Добавлена константа `KEY_DEMO_FALLBACK`
- 11-21: Новая логика `getToken()` с условным fallback
- 35-48: Добавлены `enableDemoFallback()` и `isDemoFallbackEnabled()`

---

## Файлы затронутые изменениями

### Minimal Patch
✏️ **ИЗМЕНЁН:**
- `app/src/main/java/com/example/openway/util/TokenProvider.kt` (строки 1-4, 10-16, 29-33)

✅ **НЕ ИЗМЕНЕНЫ:**
- `MainActivity.kt` — все call sites работают корректно
- `AuthRepository.kt` — saveToken() работает как прежде
- `BleClient.kt` — принимает токен как параметр
- `build.gradle.kts` — BuildConfig.DEMO_DRF_TOKEN остаётся (но не используется)

---

### Optional Patch
✏️ **ИЗМЕНЁН:**
- `app/src/main/java/com/example/openway/util/TokenProvider.kt` (весь файл: +15 строк)

✅ **НЕ ИЗМЕНЕНЫ:**
- Все остальные файлы (как в Minimal)

---

## Утверждение патча 🚦

### ⏸️ Статус: ЖДЁТ ОДОБРЕНИЯ

**Никаких изменений ещё НЕ ПРИМЕНЕНО.**

### Варианты ответа:

1. **"approve"** → Применю **Minimal патч** (рекомендуется)
2. **"approve optional"** → Применю **Optional Dev-Flag патч**
3. **"reject"** → Не буду ничего менять
4. **"modify: ..."** → Внесу коррективы в патч перед применением

---

## ✅ PATCH APPLIED

**Дата применения:** 2025-10-18  
**Вариант:** Minimal Patch  
**Статус:** ✅ SUCCESS

### Изменённые файлы

**1. TokenProvider.kt**  
**Путь:** `app/src/main/java/com/example/openway/util/TokenProvider.kt`

**Изменения:**
- ❌ Удалён: `import com.example.openway.BuildConfig`
- ✏️ Изменён: `getToken()` — убран fallback на DEMO_DRF_TOKEN
- ✏️ Изменён: `hasToken()` — читает prefs напрямую
- ✅ Добавлены: Документирующие комментарии

**Linter:** ✅ NO ERRORS

---

### Результаты

**ДО патча:**
```kotlin
// Debug mode, первый запуск:
TokenProvider.getToken(context) // → "edee5ecede95c8089112efe70a24b0d1fef5d3c4"
TokenProvider.hasToken(context) // → true
```

**ПОСЛЕ патча:**
```kotlin
// Debug mode, первый запуск:
TokenProvider.getToken(context) // → ""
TokenProvider.hasToken(context) // → false
```

**Эффект:**
- 🔒 **Логин теперь обязателен** — нельзя использовать BLE без входа
- 🔒 **После logout требуется повторный вход** — DEMO токен недоступен
- ✅ **Основной флоу не затронут** — сохранённые токены работают как прежде

---

### Next Steps

1. **Тестирование** — Собрать debug APK и проверить сценарии из Testing Guide (Step 5)
2. **Release build** — Добавить `API_BASE_URL` в release buildType (отдельный патч)
3. **Security enhancement** — Мигрировать на EncryptedSharedPreferences (отдельный патч)

---

**Конец отчёта**  
**Patch applied successfully.**

