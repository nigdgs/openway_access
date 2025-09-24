# Android Wi-Fi Integration

## Обзор

Создана инфраструктура подключения к ESP32 для Wi-Fi прохода. UI не изменен - только добавлена технология подключения.

## Структура

```
app/src/main/java/com/example/openway/
├── data/
│   ├── SettingsStore.kt      # DataStore для ESP_IP и gate_id
│   └── TokenStore.kt         # Безопасное хранение device token
├── net/
│   └── EspClient.kt          # OkHttp клиент для ESP32
└── domain/
    ├── PassModels.kt         # Модели данных (PassResult)
    └── PassService.kt        # Фасад для интеграции с UI
```

## Использование в UI

### 1. Инициализация

```kotlin
class MainActivity : ComponentActivity() {
    private lateinit var passService: PassService
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        passService = PassService(this)
    }
}
```

### 2. Настройка параметров

```kotlin
// Установка IP ESP32
lifecycleScope.launch {
    passService.setEspIp("192.168.1.50")
}

// Установка gate_id
lifecycleScope.launch {
    passService.setGateId("gate-01")
}

// Установка device token
passService.setDeviceToken("your_device_token_here")
```

### 3. Выполнение прохода

```kotlin
lifecycleScope.launch {
    val result = passService.pass(debug = BuildConfig.DEBUG)
    result.onSuccess { passResult ->
        if (passResult.allowed) {
            // Проход разрешен
            showSuccess("Проход разрешен: ${passResult.reason}")
        } else {
            // Проход запрещен
            showError("Проход запрещен: ${passResult.reason}")
        }
    }.onFailure { error ->
        // Ошибка сети
        showError("Ошибка подключения: ${error.message}")
    }
}
```

### 4. Мониторинг настроек

```kotlin
// Отслеживание изменений IP
passService.espIpFlow.collect { ip ->
    // Обновить UI с текущим IP
}

// Отслеживание изменений gate_id
passService.gateIdFlow.collect { gateId ->
    // Обновить UI с текущим gate_id
}
```

## Контракт API

### Запрос к ESP32
```
POST http://<ESP_IP>/enter
Content-Type: application/json

{
  "token": "<device_token>",
  "gate_id": "gate-01"
}
```

### Ответ ESP32
```json
{
  "status": "ok",
  "decision": "ALLOW|DENY",
  "reason": "..."
}
```

## Безопасность

- Device token хранится в зашифрованном SharedPreferences
- ESP_IP и gate_id хранятся в DataStore (не зашифрованы, но безопасны)
- HTTP соединения с таймаутами (2s connect, 3s read)
- Автоматический retry при сетевых ошибках

## Зависимости

Добавлены в `build.gradle.kts`:
- `okhttp:4.12.0` - HTTP клиент
- `kotlinx-coroutines-android:1.8.1` - корутины
- `datastore-preferences:1.1.1` - настройки
- `security-crypto:1.1.0-alpha06` - шифрование

## Тестирование

Создан базовый тест `PassServiceTest.kt` для проверки парсинга JSON ответов.

## Примечания

- UI файлы не изменены
- Манифест обновлен только с разрешением INTERNET
- Интеграция готова для использования в существующем UI
