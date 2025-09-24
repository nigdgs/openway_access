# RUNBOOK — /api/v1/access/verify

## 1. Быстрая диагностика падения verify
1. Проверить статус контейнеров: `docker compose -f backend/compose.yml ps`.
2. Заглянуть в логи web: `docker compose -f backend/compose.yml logs -f web`.
3. Проверить health: `curl -s http://localhost:8001/health` (должно вернуть `{"status":"ok"}`).
4. Если 5xx в логах — проверить Postgres: `docker compose -f backend/compose.yml logs db` и `pg_isready`.
5. Для конкретного токена — посмотреть последние события: `docker compose -f backend/compose.yml exec web python manage.py shell -c "from apps.access.models import AccessEvent; print(list(AccessEvent.objects.order_by('-created_at')[:5]))"`.

## 2. Ротация токена устройства вручную
1. Получить пользовательский API token (если нет):
   ```bash
   http POST :8001/api/v1/auth/token username=demo password=StrongPass_123
   ```
2. Ротация токена:
   ```bash
   http POST :8001/api/v1/devices/register Authorization:"Token <api_token>" rotate:=true android_device_id="esp32-demo"
   ```
3. Убедиться, что токен обновился:
   ```bash
   http :8001/api/v1/devices/me Authorization:"Token <api_token>"
   ```

## 3. Проверка rate-limit
1. Включить агрессивный limit: `ACCESS_VERIFY_RATE=2/second` в `.env`, перезапустить `web`.
2. Выполнить 5 быстрых запросов:
   ```bash
   for i in {1..5}; do http POST :8001/api/v1/access/verify gate_id=gate-01 token=dummy; done
   ```
3. Ожидаем, что начиная с 3-го запроса `reason=RATE_LIMIT` и в логе появляется `AccessEvent(decision='DENY', reason='RATE_LIMIT')`.

## 4. Расшифровка AccessEvent.reason
- `OK` — разрешено, устройство активно, разрешения найдены.
- `TOKEN_INVALID` — токен отсутствует в БД (ошибка синхронизации).
- `DEVICE_INACTIVE` — устройство вручную деактивировано.
- `NO_PERMISSION` — пользователь/группа не привязаны к точке доступа.
- `UNKNOWN_GATE` — не создан AccessPoint с указанным `gate_id`.
- `INVALID_REQUEST` — отсутствуют обязательные поля или неверный формат.
- `RATE_LIMIT` — сработал throttle (`ScopedRateThrottle` по `access_verify`).

## 5. Ротация throttle
- Значение управляется `ACCESS_VERIFY_RATE` (строка формата `<count>/<period>`).
- Сравнить с нагрузочным профилем (см. `perf/k6_verify.js`).
- После изменения переменной перезапустить веб: `docker compose -f backend/compose.yml restart web`.

## 6. Эскалация инцидента
- Если backend недоступен > 5 минут — эскалировать дежурному (см. internal SOP).
- При подозрении на компрометацию токенов — запустить `python manage.py shell -c "from apps.devices.models import Device; Device.objects.update(auth_token='')"`, после чего обязать всех пользователей пройти ротацию.
- Для аудита выгрузить AccessEvent в CSV:
  ```bash
  docker compose -f backend/compose.yml exec web python manage.py dumpdata access.AccessEvent --indent 2 > access_events.dump.json
  ```
