# Security Scan Report — OpenWay Access

**Дата:** 2025-10-04  
**Сканированные компоненты:** Dependencies, Code (Bandit), Django Settings  
**Инструменты:** pip-audit, safety, bandit, manage.py check --deploy

---

## 📊 Executive Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| **Dependencies** | 19 | 3 | 14 | 0 | 36 |
| **Code (Bandit)** | 0 | 0 | 0 | 79 | 79 |
| **Configuration** | 1 | 2 | 2 | 0 | 5 |
| **TOTAL** | **20** | **5** | **16** | **79** | **120** |

---

## 🔴 CRITICAL Findings (требуется немедленное исправление)

### 1. Django 5.0.6 → 17 CVE (SQL Injection + DoS)

**Уязвимости:**
- **CVE-2025-57833** (CRITICAL): SQL injection в FilteredRelation
- **CVE-2024-42005** (HIGH): SQL injection в JSONField column aliases
- **CVE-2024-53908** (HIGH): SQL injection в HasKey lookup (Oracle)
- **CVE-2025-48432** (HIGH): Log injection через request.path
- + 13 DoS/timing attack уязвимостей

**Риск:** Remote Code Execution, Data Breach, Service Disruption

**Фикс:**
```bash
# 1. Обновить requirements.txt
sed -i 's/Django==5.0.6/Django==5.0.14/' requirements.txt

# 2. Пересобрать контейнер
docker compose down
docker compose up -d --build

# 3. Проверить миграции
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check --deploy

# 4. Запустить тесты
docker compose exec web pytest tests/
```

**Статус:** ✅ ИСПРАВЛЕНО в requirements.txt

---

### 2. Gunicorn 21.2.0 → 2 CVE (HTTP Request Smuggling)

**Уязвимости:**
- **CVE-2024-6827** (CRITICAL): TE.CL request smuggling
- **CVE-2024-1135** (HIGH): Conflicting Transfer-Encoding headers

**Последствия:**
- Cache poisoning
- Security bypass (доступ к защищённым endpoints)
- SSRF, XSS, DoS

**Фикс:**
```bash
# 1. Обновить requirements.txt
sed -i 's/gunicorn==21.2.0/gunicorn==22.0.0/' requirements.txt

# 2. Пересобрать
docker compose down
docker compose up -d --build

# 3. Проверить запуск
docker compose logs web | grep gunicorn
```

**Статус:** ✅ ИСПРАВЛЕНО в requirements.txt

---

### 3. PostgreSQL дефолтный пароль "nfc"

**Текущее состояние:**
```python
# settings/base.py
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "nfc")  # Слабый дефолт!
```

**.env (текущий):**
```
POSTGRES_PASSWORD=nfc  # ⚠️ КРИТИЧНО для production!
```

**Риск:** Брутфорс в production, несанкционированный доступ к БД

**Фикс:**
```bash
# 1. Сгенерировать сильный пароль
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Пример: DJa8Kx_YzL9QmR3pW5tN7vH2cF4gB6sA8nU0eI1oX9Z

# 2. Обновить .env.prod
cat > .env.prod << 'EOF'
POSTGRES_DB=nfc_access
POSTGRES_USER=nfc
POSTGRES_PASSWORD=<СГЕНЕРИРОВАННЫЙ_ПАРОЛЬ_32_CHARS>
DB_HOST=db
DB_PORT=5432
...
EOF

# 3. Пересоздать БД контейнер (ВНИМАНИЕ: потеря данных!)
docker compose down -v
docker compose --env-file .env.prod up -d

# 4. Восстановить данные из бэкапа (если есть)
gunzip < ops/backups/openway_latest.sql.gz | \
  docker compose exec -T db psql -U nfc -d nfc_access
```

**Статус:** ⚠️ ТРЕБУЕТСЯ ДЕЙСТВИЕ перед production

---

## 🟡 HIGH Priority (исправить до production)

### 4. CORS Middleware отсутствует

**Проблема:** API недоступен из браузерных приложений на другом origin.

**Текущий код:**
```python
INSTALLED_APPS = [
    ...
    # ❌ 'corsheaders' отсутствует
]
```

**Фикс:** ✅ УЖЕ ПРИМЕНЁН

```python
# settings/base.py
INSTALLED_APPS = [
    ...
    "corsheaders",  # ✅
    ...
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # ✅ Сразу после SecurityMiddleware
    ...
]

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080"
).split(",")
CORS_ALLOW_CREDENTIALS = True
```

**Production настройка:**
```bash
# .env.prod
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

### 5. DEFAULT_PERMISSION_CLASSES = AllowAny

**Проблема:** По умолчанию все новые эндпоинты будут публичными.

**Текущий код:**
```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",  # ⚠️
    ],
}
```

**Риск:** Легко забыть добавить `IsAuthenticated` на новый эндпоинт.

**Рекомендуемый фикс:**
```python
REST_FRAMEWORK = {
    ...
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",  # ✅ По умолчанию защищено
    ],
}
```

**Затем явно разрешить публичные эндпоинты:**
```python
class AccessVerifyView(APIView):
    permission_classes = [AllowAny]  # Явное разрешение
    ...
```

**Статус:** ⚠️ ТРЕБУЕТСЯ ОБСУЖДЕНИЕ (может сломать текущую логику)

---

### 6. pip 25.0.1 → CVE-2025-8869 (Arbitrary File Overwrite)

**Уязвимость:** Symlink/hardlink escape в sdist extraction.

**Риск:** Overwrite произвольных файлов при `pip install` malicious sdist.

**Фикс:**
```bash
# Обновить pip внутри контейнера (когда выйдет 25.3)
docker compose exec web pip install --upgrade pip

# Или в Dockerfile:
RUN pip install --upgrade pip==25.3
```

**Статус:** ⚠️ Ждём релиз pip 25.3 (Q1 2025)

---

## 🟢 MEDIUM Priority

### 7. ALLOWED_HOSTS="*" в base.py

**Проблема:** Host header poisoning в dev режиме.

**Текущий код:**
```python
# base.py
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")  # ⚠️
```

**Статус:** ✅ Переопределяется в prod.py, но лучше убрать дефолт "*"

**Рекомендуемый фикс:**
```python
# base.py
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
```

---

### 8. SECRET_KEY с дефолтом "dev-secret"

**Проблема:** Если забыть установить `DJANGO_SECRET_KEY` в production → слабый ключ.

**Текущий код:**
```python
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret")  # ⚠️
```

**Текущий .env:**
```
DJANGO_SECRET_KEY=f1b3f133cffc8e32b9be4b547b2f22319abb7f8145291c5b244928aa6c3a60c7c0582c37e3ba699bae4c30a04b83d529478c2635cd75a86af29c1fee8bd7fa69
```
✅ Криптостойкий (128 hex chars)

**Рекомендуемый фикс (для prod.py):**
```python
# prod.py
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # Fail fast если не установлен
```

---

## ✅ Passed Security Checks

### Code Security (Bandit)
- ✅ 0 High severity issues
- ✅ 0 Medium severity issues
- ✅ 1860 lines scanned

### Django Security Settings (prod.py)
- ✅ CSRF Protection enabled
- ✅ SESSION_COOKIE_SECURE = True
- ✅ SESSION_COOKIE_HTTPONLY = True
- ✅ CSRF_COOKIE_SECURE = True
- ✅ SECURE_SSL_REDIRECT = True
- ✅ SECURE_HSTS_SECONDS = 31536000 (1 year)
- ✅ SECURE_HSTS_INCLUDE_SUBDOMAINS = True
- ✅ SECURE_HSTS_PRELOAD = True
- ✅ SECURE_CONTENT_TYPE_NOSNIFF = True
- ✅ SECURE_BROWSER_XSS_FILTER = True
- ✅ X_FRAME_OPTIONS = 'DENY'

### Secrets Management
- ✅ SECRET_KEY уникальный, НЕ дефолтный
- ✅ .env в .gitignore
- ✅ .env.example не содержит реальных секретов

---

## 🛠️ Fix Plan (Automated)

### Immediate Actions (Critical)

```bash
#!/bin/bash
# security-fix.sh — Автоматическое исправление критических уязвимостей

set -e

echo "=== Security Fix Plan ==="

# 1. Обновить зависимости (УЖЕ СДЕЛАНО)
echo "✅ Django 5.0.6 → 5.0.14 (requirements.txt updated)"
echo "✅ Gunicorn 21.2.0 → 22.0.0 (requirements.txt updated)"
echo "✅ CORS middleware added"

# 2. Пересобрать контейнер
echo ""
echo "Step 1: Rebuilding containers..."
docker compose down
docker compose up -d --build

# 3. Проверить миграции
echo ""
echo "Step 2: Checking migrations..."
docker compose exec web python manage.py migrate --check

# 4. Запустить тесты
echo ""
echo "Step 3: Running tests..."
docker compose exec web pytest tests/ -q

# 5. Security checks
echo ""
echo "Step 4: Security validation..."
docker compose exec web python manage.py check --deploy

# 6. Verify versions
echo ""
echo "Step 5: Verifying versions..."
docker compose exec web python -c "import django; print(f'Django: {django.__version__}')"
docker compose exec web python -c "import gunicorn; print(f'Gunicorn: {gunicorn.__version__}')"

echo ""
echo "=== ✅ Security fixes applied ==="
echo ""
echo "⚠️  MANUAL ACTION REQUIRED:"
echo "1. Update POSTGRES_PASSWORD in production"
echo "2. Review DEFAULT_PERMISSION_CLASSES (consider IsAuthenticated)"
echo "3. Set CORS_ALLOWED_ORIGINS for production domains"
echo "4. Test CORS from frontend application"
```

---

## 📋 Production Deployment Checklist

### Before Deployment

- [ ] Update Django to 5.0.14+
- [ ] Update Gunicorn to 22.0.0+
- [ ] Generate strong POSTGRES_PASSWORD (32+ chars)
- [ ] Set DJANGO_SECRET_KEY (50+ chars, unique)
- [ ] Set DJANGO_ALLOWED_HOSTS (real domains only)
- [ ] Set CORS_ALLOWED_ORIGINS (real frontend origins)
- [ ] DJANGO_SETTINGS_MODULE=accessproj.settings.prod
- [ ] Run `manage.py check --deploy` (0 warnings)
- [ ] Run full test suite
- [ ] Backup current database
- [ ] Set up HTTPS reverse proxy (Nginx/Traefik)
- [ ] Configure firewall (block direct DB access)
- [ ] Set up monitoring (Sentry/Prometheus)
- [ ] Document incident response plan

### After Deployment

- [ ] Verify HTTPS redirect works
- [ ] Test CORS from frontend
- [ ] Check access logs for anomalies
- [ ] Monitor error rates (Sentry)
- [ ] Schedule regular security scans (weekly)
- [ ] Enable automated dependency updates (Dependabot/Renovate)

---

## 🔄 Continuous Security

### Automated Scanning

```bash
# Добавить в CI/CD pipeline (.github/workflows/security.yml)
name: Security Scan

on: [push, pull_request, schedule]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Dependency Scan
        run: |
          pip install pip-audit safety
          pip-audit -r requirements.txt
          safety check -r requirements.txt
      
      - name: Code Scan
        run: |
          pip install bandit
          bandit -r . -ll -f json -o bandit-report.json
      
      - name: Django Security Check
        run: |
          docker compose exec web python manage.py check --deploy
```

### Monthly Tasks

- [ ] Review pip-audit report
- [ ] Update dependencies (patch versions)
- [ ] Review access logs
- [ ] Rotate secrets (if compromised)
- [ ] Update documentation

### Quarterly Tasks

- [ ] Full penetration test
- [ ] Review OWASP Top 10 compliance
- [ ] Update security policies
- [ ] Team security training

---

## 📚 References

- [Django Security Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CVE Database](https://cve.mitre.org/)
- [Gunicorn Security Advisory](https://github.com/benoitc/gunicorn/security/advisories)

---

**Report Generated:** 2025-10-04  
**Next Review:** 2025-11-04 (monthly)

