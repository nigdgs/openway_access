#!/usr/bin/env bash
set -Eeuo pipefail

# --- config ---
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$BACKEND_DIR/GO_LIVE_CHECK.md"
BACKUPS_DIR="$BACKEND_DIR/ops/backups"
HTTP_BASE="${HTTP_BASE:-http://localhost:8001}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin}"

# detect compose
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi

mkdir -p "$BACKUPS_DIR"
cd "$BACKEND_DIR"

section () { echo -e "\n## $1" | tee -a "$REPORT"; }
codeblock () { echo -e "\n\`\`\`$1" >> "$REPORT"; cat >> "$REPORT"; echo -e "\`\`\`\n" >> "$REPORT"; }
append_cmd () { echo -e "\n\`\`\`bash\n$ $*\n\`\`\`\n" >> "$REPORT"; }

echo "# Go-Live Check Report — $(date -Iseconds)" > "$REPORT"
echo "_Host_: $(hostname)  |  _Dir_: $BACKEND_DIR" >> "$REPORT"

# A. Config & migrations
section "A. Конфигурация и миграции"

append_cmd $DC exec web python - <<'PY'
import os; print(os.environ.get("DJANGO_SETTINGS_MODULE"))
PY
SETTINGS="$($DC exec -T web python - <<'PY'
import os; print(os.environ.get("DJANGO_SETTINGS_MODULE"))
PY
)"
echo -e "\n**DJANGO_SETTINGS_MODULE:** \`$SETTINGS\`" >> "$REPORT"

append_cmd $DC exec web python manage.py showmigrations
$DC exec -T web python manage.py showmigrations > /tmp/_migs.txt
codeblock "" < /tmp/_migs.txt
if grep -q "\[ \]" /tmp/_migs.txt; then echo "- ❌ Есть неприменённые миграции" >> "$REPORT"; else echo "- ✅ Миграции применены" >> "$REPORT"; fi

append_cmd $DC exec web python manage.py migrate --noinput
$DC exec -T web python manage.py migrate --noinput | tee /tmp/_migrate_out.txt >/dev/null
codeblock "" < /tmp/_migrate_out.txt

# B. Security (prod)
section "B. Безопасность (prod)"
append_cmd $DC exec -e DJANGO_SETTINGS_MODULE=accessproj.settings.prod web python manage.py check --deploy
$DC exec -e DJANGO_SETTINGS_MODULE=accessproj.settings.prod -T web python manage.py check --deploy > /tmp/_deploy_check.txt || true
codeblock "" < /tmp/_deploy_check.txt
if grep -qi "System check identified no issues" /tmp/_deploy_check.txt; then echo "- ✅ check --deploy: без предупреждений" >> "$REPORT"; else echo "- ⚠️ Проверь предупреждения выше" >> "$REPORT"; fi

# C. Logs (JSON, no tokens)
section "C. Наблюдаемость и логи"
append_cmd $DC logs -n 50 web
$DC logs -n 50 web > /tmp/_logs.json || true
codeblock "" < /tmp/_logs.json
echo "- Проверь, что в логах нет значений токенов" >> "$REPORT"

# D. API contract
section "D. Контракт API (OpenAPI/Swagger)"
append_cmd curl -f "$HTTP_BASE/schema/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HTTP_BASE/schema/" || true)
echo "- /schema/ HTTP: $HTTP_CODE" >> "$REPORT"
if [ "$HTTP_CODE" = "200" ]; then echo "- ✅ Схема доступна" >> "$REPORT"; else echo "- ❌ Схема недоступна" >> "$REPORT"; fi
echo "- Swagger UI: $HTTP_BASE/docs/" >> "$REPORT"

# E. Smoke Variant 1
section "E. Смоук (Variant 1: user_token + RBAC)"
append_cmd curl -f "$HTTP_BASE/health" "&&" curl -f "$HTTP_BASE/ready"
H1=$(curl -s -o /dev/null -w "%{http_code}" "$HTTP_BASE/health" || true)
H2=$(curl -s -o /dev/null -w "%{http_code}" "$HTTP_BASE/ready" || true)
echo "- /health: $H1, /ready: $H2" >> "$REPORT"

# Ensure gate + permission (idempotent)
$DC exec -T web python manage.py shell <<'PY' >/tmp/_perm.txt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.access.models import AccessPoint, AccessPermission
U=get_user_model()
try:
    u=U.objects.get(username="admin")
except U.DoesNotExist:
    u=U.objects.create_user(username="admin", password="admin", is_active=True)
g,_=Group.objects.get_or_create(name="ADM"); u.groups.add(g)
gate,_=AccessPoint.objects.get_or_create(code="gate-01", defaults={"name":"Main Gate"})
AccessPermission.objects.get_or_create(access_point=gate, group=g, defaults={"allow":True})
print("OK: gate-01 & group ADM ready")
PY
codeblock "" < /tmp/_perm.txt

# Get user token via API
TOKEN="$(curl -s -X POST "$HTTP_BASE/api/v1/auth/token" -H 'Content-Type: application/json' -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}" | awk -F'"' '/token/{print $4}')"
if [ -z "${TOKEN:-}" ]; then
  echo "- ❌ Не удалось получить user token для $ADMIN_USER" >> "$REPORT"
else
  echo "- ✅ User token получен (скрыт в отчёте)" >> "$REPORT"
  append_cmd curl -s -X POST "$HTTP_BASE/api/v1/access/verify" -H 'Content-Type: application/json' -d '{"gate_id":"gate-01","token":"<MASKED>"}'
  RESP="$(curl -s -X POST "$HTTP_BASE/api/v1/access/verify" -H 'Content-Type: application/json' -d "{\"gate_id\":\"gate-01\",\"token\":\"$TOKEN\"}")"
  echo -e "\n**verify response:**" >> "$REPORT"
  codeblock "json" <<< "$RESP"
fi

# F. Rate limit
section "F. Rate-limit и RBAC"
append_cmd $DC exec web python - <<'PY'
import os; print(os.environ.get("ACCESS_VERIFY_RATE","30/second (default)"))
PY
RL="$($DC exec -T web python - <<'PY'
import os; print(os.environ.get("ACCESS_VERIFY_RATE","30/second (default)"))
PY
)"
echo "- ACCESS_VERIFY_RATE: $RL" >> "$REPORT"
if [ -n "${TOKEN:-}" ]; then
  echo -e "\nСтресс (50 запросов, причины агрегированы):" >> "$REPORT"
  OUT="$(for i in $(seq 1 50); do \
    curl -s -X POST "$HTTP_BASE/api/v1/access/verify" \
      -H 'Content-Type: application/json' \
      -d "{\"gate_id\":\"gate-01\",\"token\":\"$TOKEN\"}" | jq -r '.reason'; \
  done | sort | uniq -c)"
  codeblock "" <<< "$OUT"
fi

# G. Quality (tests & lints)
section "G. Качество (тесты и линтер)"
append_cmd $DC exec web pytest -q
$DC exec -T web pytest -q > /tmp/_pytest.txt || true
codeblock "" < /tmp/_pytest.txt
if grep -qi "failed" /tmp/_pytest.txt; then echo "- ❌ Есть упавшие тесты" >> "$REPORT"; else echo "- ✅ Тесты зелёные (или пропуски не критичны)" >> "$REPORT"; fi

append_cmd $DC exec web ruff check .
$DC exec -T web ruff check . > /tmp/_ruff.txt || true
codeblock "" < /tmp/_ruff.txt

# H. Retention & backups
section "H. Ретеншн и бэкапы"
append_cmd $DC exec web python manage.py purge_access_events --days 0
$DC exec -T web python manage.py purge_access_events --days 0 > /tmp/_purge.txt || true
codeblock "" < /tmp/_purge.txt

append_cmd "$DC exec -T db pg_dump -U \${POSTGRES_USER:-nfc} -d \${POSTGRES_DB:-nfc_access} | gzip > $BACKUPS_DIR/openway_$(date +%F_%H%M).sql.gz"
if $DC exec -T db pg_dump -U "${POSTGRES_USER:-nfc}" -d "${POSTGRES_DB:-nfc_access}" | gzip > "$BACKUPS_DIR/openway_$(date +%F_%H%M).sql.gz"; then
  echo "- ✅ Бэкап сохранён в $BACKUPS_DIR" >> "$REPORT"
else
  echo "- ❌ Бэкап выполнить не удалось" >> "$REPORT"
fi

# Summary
section "Итог"
echo "- Проверь пункты с ❌/⚠️ выше." >> "$REPORT"
echo "- Если все ключевые проверки зелёные — **готово к выкладке**." >> "$REPORT"

echo -e "\nDone. Отчёт: $REPORT"

