
# Android (Kotlin) — HCE каркас

Минимальный каркас HostApduService для эмуляции карты.
Проект не полноценный Gradle‑проект, а скелет файлов с ключевыми классами и манифестом — перенесите их в ваш Android‑проект.

## Файлы
- `app/src/main/AndroidManifest.xml` — объявление сервиса HCE
- `app/src/main/res/xml/apduservice.xml` — AID
- `app/src/main/java/com/example/hce/MyHostApduService.kt` — обработчик APDU
