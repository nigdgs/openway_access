
# Проект: Мобильное приложение современной пропускной системы (ESP32 + PN532 + Android HCE + Django)

Этот репозиторий — **каркас архитектуры**: бэкенд (Django/DRF), прошивка контроллера (ESP32 + PN532), Android‑клиент (HCE), инфраструктура (docker-compose), документация.
Используйте как стартовую точку для вашего MVP и дальнейшей доработки.

## Структура
```
access-control-skeleton/
  backend/            # Django + DRF + PostgreSQL (каркас, минимальные эндпоинты)
  firmware/           # ESP32 + PN532 (скелет PlatformIO/Arduino)
  mobile-android/     # Android (Kotlin) + HostApduService (HCE) каркас
  infra/              # docker-compose + reverse-proxy (пример)
  docs/               # протокол, контракты API
```
