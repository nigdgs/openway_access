# Android Snapshot — 2025-10-17, commit e8dcd7f (dirty)

## Проект и сборка
- Корень Android: `android/OpenWay/`
- Modules: `:app` (android/OpenWay/settings.gradle.kts:22-24)
- SDK: compileSdk=36, minSdk=26, targetSdk=36 (android/OpenWay/app/build.gradle.kts:9-15)
- Kotlin=2.0.21, AGP=8.12.3 (android/OpenWay/gradle/libs.versions.toml:2-3)
- Compose BOM: 2024.09.00 (android/OpenWay/gradle/libs.versions.toml:10-11)
- buildTypes: release minifyEnabled=false, proguard-rules.pro (android/OpenWay/app/build.gradle.kts:26-33)
- BuildConfig fields: DEMO_DRF_TOKEN, SERVICE_UUID, CHAR_UUID, BLE_NAME_HINT (android/OpenWay/app/build.gradle.kts:20-24)

## Зависимости
| Категория | Координаты/версия | Ссылки |
|---|---|---|
| Compose BOM | androidx.compose:compose-bom:2024.09.00 | android/OpenWay/gradle/libs.versions.toml:10,22; app/build.gradle.kts:53,64 |
| Core KTX | androidx.core:core-ktx:1.10.1 | libs.versions.toml:4,16; app/build.gradle.kts:50 |
| Lifecycle | androidx.lifecycle:lifecycle-runtime-ktx:2.6.1 | libs.versions.toml:8,20; app/build.gradle.kts:51 |
| Activity Compose | androidx.activity:activity-compose:1.8.0 | libs.versions.toml:9,21; app/build.gradle.kts:52 |
| Compose UI/Material3 | ui, ui-graphics, ui-tooling-preview, material3 | libs.versions.toml:22-32; app/build.gradle.kts:54-57,67 |
| Foundation + Layout | 1.9.1 / 1.9.2 | libs.versions.toml:11,13,30,32; app/build.gradle.kts:58,60 |
| Navigation Compose | 2.9.4 | libs.versions.toml:12,31; app/build.gradle.kts:59 |
| Test (Junit/Espresso) | junit:4.13.2, espresso:3.5.1 | libs.versions.toml:5,7,18-19; app/build.gradle.kts:61-66 |

Нет Retrofit/OkHttp/Moshi/Ktor/Hilt/Koin/DataStore/Room/WorkManager в зависимостях (подтверждено по app/build.gradle.kts:48-68).

## Network & Security
- INTERNET permission в манифесте отсутствует (android/OpenWay/app/src/main/AndroidManifest.xml:1-41) — сетевые вызовы из приложения не настроены.
- Network security config не задан; cleartextTrafficPermitted не указано.
- TargetSdk=36 (app/build.gradle.kts:14-15) — на Android 9+ cleartext HTTP запрещён без networkSecurityConfig/флага.

## Auth & Token Storage
- Токен хранится в SharedPreferences под ключом `user_token`; при отсутствии — берётся из BuildConfig.DEMO_DRF_TOKEN (android/OpenWay/app/src/main/java/com/example/openway/util/TokenProvider.kt:6-13).
- Клиента /api/v1/auth/token в коде не найдено; логика логина на экране `LoginScreen` не вызывает сеть (android/OpenWay/app/src/main/java/com/example/openway/LoginScreen.kt:186-201).
- Подстановка токена в сетевые запросы отсутствует (сетевой слой отсутствует).

## BLE
- Permissions: BLUETOOTH_SCAN/CONNECT (12+), FINE/COARSE LOCATION (<12), features BLE LE (android/OpenWay/app/src/main/AndroidManifest.xml:5-20).
- Runtime permissions: запрашиваются в `MainActivity.ensureBlePermsAndSend` (android/OpenWay/app/src/main/java/com/example/openway/MainActivity.kt:78-97).
- BLE клиент: запись токена в характеристику по MAC-адресу; UUID берутся из `BleConfig` (android/OpenWay/app/src/main/java/com/example/openway/ble/BleClient.kt:34-48,114-121,129-138; BleConfig.kt:5-17).
- Источник токена: `TokenProvider.getToken()` (SharedPreferences/BuildConfig) (MainActivity.kt:78-81; TokenProvider.kt:10-13).

## UI/Навигация
- Навигация Compose: `NavHost` с `mainScreen` и `loginScreen` (android/OpenWay/app/src/main/java/com/example/openway/MainActivity.kt:116-124).
- `LoginScreen` — UI ввода, переход на mainScreen без сети (LoginScreen.kt:186-201).
- Основной экран запускает BLE-сценарий отправки токена при нажатии на кнопку (MainActivity.kt:212-221).

## Тесты/Proguard/CI
- Proguard: файл существует, но правил для DTO/retrofit/moshi нет (android/OpenWay/app/proguard-rules.pro:1-21).
- Инструментальные/юнит тесты зависимости подключены; специфичных тестов в repo папке app/src/test|androidTest минимум (по структуре каталога).
- Gradle wrapper присутствует; запуск tooling не удался: `./android/OpenWay/gradlew --version` — FAIL
```
java.io.FileNotFoundException: /Users/aleksandr/.gradle/wrapper/dists/gradle-8.13-bin/... .lck (Operation not permitted)
```
— вероятно из-за sandbox/прав доступа.

## Гэп-анализ и Next Steps
- Нет сетевого слоя (Retrofit/OkHttp) и INTERNET permission — невозможно вызвать /auth/token из приложения.
- Токен берётся из BuildConfig.DEMO_DRF_TOKEN — требуется реализовать логин и безопасное хранение (EncryptedSharedPreferences или DataStore + MasterKey).
- Нет базового URL (BuildConfig/API_BASE_URL) и сетевой конфигурации (cleartext/HTTPS, networkSecurityConfig).
- BLE использует статический MAC — нужно сканирование/паринг/выбор устройства или стабильный MAC.

Next steps (без правок кода, указаны точки входа):
- Добавить INTERNET permission и (при HTTP) networkSecurityConfig для dev (AndroidManifest.xml).
- Ввести BuildConfig.API_BASE_URL и зависимости Retrofit/OkHttp + конвертер (app/build.gradle.kts), создать API-интерфейсы для `/api/v1/auth/token` и `/api/v1/access/verify`.
- Реализовать репозиторий авторизации, вызывать `/auth/token` из `LoginScreen`, сохранять токен в EncryptedSharedPreferences или DataStore (TokenProvider.kt).
- Добавить interceptor для подстановки токена, обработку 401/400, прогресс/ошибки в UI.
- Опционально: сканирование BLE и конфигурация `BleConfig.DEVICE_MAC` из настроек.
