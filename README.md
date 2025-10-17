# OpenWay — Local Quickstart

## Что здесь есть
- Backend: Django + DRF + PostgreSQL в Docker Compose (порт 8001).
- Android: модуль `:app` (Compose UI, BLE клиент для отправки токена на ESP32).
- ESP32: прошивка PlatformIO (BLE + Wi‑Fi + HTTP verify на backend).

## Требуется
- Docker Desktop (WSL2 на Windows).
- Android Studio (Arctic/новее) + SDK платформы 36.
- (Опц.) PlatformIO для сборки ESP32.

## Порты и адреса
- Хост: `http://127.0.0.1:8001`
- Android эмулятор: `http://10.0.2.2:8001`
- Телефон/ESP32 (LAN): `http://<LAN_IP>:8001`

## Как запустить backend локально
```bash
cd backend
cp .env.local.example .env  # заполните переменные
docker compose up -d --build
# дождитесь health БД, затем
docker compose exec web python manage.py migrate
```

## Демо-данные и smoke
```bash
# создайте пользователей и права (пример вашей команды/management-скрипта, если есть)
# затем проверьте:
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/docs/
curl -s http://127.0.0.1:8001/schema/
# получить токен (если учётка создана)
curl -X POST http://127.0.0.1:8001/api/v1/auth/token -d 'username=demo&password=pass1234'
# verify (замените <TOKEN>)
curl -X POST http://127.0.0.1:8001/api/v1/access/verify -H 'Content-Type: application/json' \
  -d '{"gate_id":"front_door","token":"<TOKEN>"}'
```

## Траблшутинг
- Порт 8000/8001 занят → поменяйте mapping в compose или используйте 8001.
- Эмулятор Android использует `10.0.2.2` для доступа к хосту.
- 429 RATE_LIMIT → уменьшите частоту запросов или увеличьте `ACCESS_VERIFY_RATE`.
- Apple Silicon: при необходимости укажите `--platform=linux/amd64` в `docker build`.
- Windows: убедитесь, что WSL2 включен и Firewall пропускает локальные порты.

## Где править конфиги
- Backend: `backend/.env` (см. шаблон `.env.local.example`).
- Android: `android/OpenWay/app/build.gradle.kts` (BuildConfig), манифест/сетевой конфиг.
- ESP32: `bluetooth_android_esp32/platformio.ini` и константы в `src/main.cpp`.
