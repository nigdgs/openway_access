# Production Readiness Documentation

## Overview

This document describes the production hardening changes applied to the OpenWay Access Django backend. All changes are designed to improve security, observability, reliability, and maintainability for production deployment.

## Changes Summary

### 1. Security Updates ✓

**What Changed:**
- Updated `requirements.txt` to use `Django~=5.0.14` (compatible range notation)
- Upgraded pip in Dockerfile build process
- Ran security audits with `pip-audit` and `bandit`

**Security Audit Results:**
- **pip-audit**: Found 2 known vulnerabilities in Django 5.0.14 (GHSA-7xr5-9hcq-chf9, GHSA-6w2m-r2m5-xq5w)
  - Fixed in Django 4.2.22+, 5.1.10+, 5.2.2+
  - Note: These are in newer series; 5.0.14 is the latest patch in 5.0.x
  - Recommendation: Monitor Django releases and consider upgrading to 5.1+ or LTS 4.2 series
- **bandit**: Found 5 low-severity issues, all in test code (hardcoded test passwords/tokens)
  - These are acceptable in test environments

**Files Changed:**
- `requirements.txt`
- `Dockerfile`
- `reports/security.txt` (audit results)

**Patch:** `fixes/01_security_upgrades.patch`

### 2. Health & Readiness Endpoints ✓

**What Changed:**
- Added Kubernetes-style aliases: `/healthz` and `/readyz`
- Existing `/health` and `/ready` endpoints remain unchanged
- Added test coverage for new endpoints

**Endpoints:**
- `/health` → Simple liveness check (200 OK)
- `/healthz` → Alias for `/health`
- `/ready` → Database connection check (200 if DB available, 503 otherwise)
- `/readyz` → Alias for `/ready`

**Files Changed:**
- `core/urls.py`
- `tests/api/test_healthz_readyz.py` (new)

**Patch:** `fixes/02_health_endpoints.patch`

### 3. DRF Permission Defaults ✓

**What Changed:**
- Changed default permission from `AllowAny` to `IsAuthenticated`
- Explicitly marked public endpoints with `@permission_classes([AllowAny])`
- Schema and docs endpoints configured for public access

**Public Endpoints:**
- `/health`, `/healthz`, `/ready`, `/readyz`
- `/schema/`, `/docs/`
- `/admin/` (Django admin - has its own authentication)

**Private Endpoints (require authentication):**
- All `/api/v1/*` endpoints

**Files Changed:**
- `accessproj/settings/base.py` (REST_FRAMEWORK, SPECTACULAR_SETTINGS)
- `core/views.py` (health/ready decorators)
- `tests/api/test_permissions.py` (new)

**Patch:** `fixes/03_permissions_defaults.patch`

### 4. JSON Logging ✓

**What Changed:**
- Added structured JSON logging for production environments
- Implemented request tracking with `X-Request-ID` header
- Added access log middleware for automatic request/response logging

**Features:**
- **JSONFormatter**: Formats logs as JSON with fields: `ts`, `level`, `logger`, `message`
- **RequestIdMiddleware**: Adds/forwards `X-Request-ID` header for request tracing
- **AccessLogMiddleware**: Logs every request with: `method`, `path`, `status`, `duration_ms`, `user_id`

**Log Fields:**
```json
{
  "ts": "2025-10-04T14:10:30.124690Z",
  "level": "INFO",
  "logger": "django.request",
  "message": "GET /health 200 3ms",
  "request_id": "1274e6f1-79dc-4ecd-abd3-cac72c25bcdf",
  "method": "GET",
  "path": "/health",
  "status": 200,
  "duration_ms": 3
}
```

**Files Changed:**
- `accessproj/settings/logging_json.py` (new)
- `accessproj/settings/base.py` (imports logging config, adds middleware)
- `core/middleware.py` (new)

**Patch:** `fixes/04_json_logging.patch`

### 5. Docker Hardening ✓

**What Changed:**
- Added non-root user (`app`, uid 1000) to Dockerfile
- Container now runs as `USER 1000:1000` instead of root
- Added healthcheck to `compose.yml` for automatic health monitoring

**Security Benefits:**
- Reduced attack surface (non-root user)
- Better container security practices
- Automatic health monitoring and restart on failure

**Healthcheck Configuration:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
  interval: 10s
  timeout: 3s
  retries: 3
```

**Files Changed:**
- `Dockerfile`
- `compose.yml`

**Patch:** `fixes/05_docker_nonroot_and_healthcheck.patch`

### 6. Nginx + TLS Configuration ✓

**What Delivered:**
- Production-ready Nginx configuration template
- Automated Let's Encrypt setup script for Ubuntu/Debian

**Files Created:**
- `ops/nginx/conf.d/app.conf`: Nginx configuration with:
  - HTTP to HTTPS redirect (commented out until TLS is configured)
  - Static files serving (`/static/`, `/media/`)
  - Proxy headers (`X-Real-IP`, `X-Forwarded-For`, `X-Request-ID`)
  - Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
  - HSTS configuration (commented out until TLS is active)
  - Health endpoint configuration (no logging)
  
- `ops/tls/setup_certbot.sh`: Automated setup script:
  - Installs Nginx and Certbot
  - Obtains Let's Encrypt certificates
  - Configures automatic renewal via cron
  - **DO NOT RUN AUTOMATICALLY** - Manual review and customization required

**Setup Instructions:**
1. Edit `ops/tls/setup_certbot.sh` to set your domain and email
2. Ensure DNS points to your server
3. Run the script as root on your production server
4. Update Django `ALLOWED_HOSTS` to include your domain

**Patch:** `fixes/06_nginx_tls_assets.patch`

### 7. Database Backup Scripts ✓

**What Delivered:**
- Automated PostgreSQL backup script with rotation
- Safe database restore script with confirmations

**Files Created:**
- `scripts/backup.sh`:
  - Creates compressed backups (`*.sql.gz`)
  - Stores in `ops/backups/` directory
  - Automatic rotation (keeps last N backups, default 7)
  - Reads configuration from environment variables
  
- `scripts/restore.sh`:
  - Restores database from compressed backup
  - Creates pre-restore backup automatically
  - Safety confirmations (especially for production)
  - Lists available backups if none specified

**Usage Examples:**
```bash
# Backup
export POSTGRES_DB=nfc_access
export POSTGRES_USER=nfc
export POSTGRES_PASSWORD=yourpassword
./scripts/backup.sh

# Restore
./scripts/restore.sh ops/backups/nfc_access_2025-10-04_1559.sql.gz
```

**Environment Variables:**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DB_HOST`, `DB_PORT`
- `BACKUP_DIR` (default: `ops/backups`)
- `KEEP_BACKUPS` (default: 7)

**Patch:** `fixes/07_db_backup_scripts.patch`

### 8. CI/CD Pipeline ✓

**What Delivered:**
- GitHub Actions workflow for continuous integration

**File Created:**
- `.github/workflows/ci.yml`:
  - Matrix testing (Python 3.12)
  - PostgreSQL service container
  - Linting: `ruff`, `mypy`, `bandit`, `pip-audit`
  - Testing: `pytest` with coverage reporting
  - Coverage upload to Codecov (optional)
  - Docker build job (commented out, ready for GHCR)

**CI Steps:**
1. Code checkout
2. Python setup with pip caching
3. Install dependencies
4. Run linters (non-blocking on failures)
5. Run security scanners
6. Run pytest test suite
7. Generate coverage report

**Docker Build:**
- Currently commented out
- Ready to enable when GHCR is configured
- Builds and pushes on `main`/`develop` branch pushes

**Patch:** `fixes/08_ci_pipeline.patch`

## Testing & Validation

### Test Results

**Unit Tests:**
- **Status:** ✓ PASSED
- **Results:** 51 passed, 1 skipped
- **Duration:** 3.22s
- **Report:** `reports/pytest.txt`

**Code Coverage:**
- **Overall:** 67%
- **Detailed report:** `reports/coverage.txt`
- **Key modules:**
  - `apps/api/v1/views.py`: 94%
  - `core/middleware.py`: 100%
  - `accessproj/settings/base.py`: 100%

**E2E Tests:**
- **Status:** ✓ PASSED
- **Tests performed:**
  - ✓ `/healthz` endpoint (200 OK)
  - ✓ `/readyz` endpoint (200 OK)
  - ✓ User authentication token retrieval
  - ✓ Access verification DENY/NO_PERMISSION
  - ✓ Access verification TOKEN_INVALID
  - ✓ Access verification UNKNOWN_GATE
  - ✓ OpenAPI schema endpoint
- **Report:** `reports/e2e.jsonl` (JSONL format)

### Health Check Verification

**Local Testing:**
```bash
# Health endpoints
curl http://localhost:8001/health   # → {"status": "ok"}
curl http://localhost:8001/healthz  # → {"status": "ok"}
curl http://localhost:8001/ready    # → {"status": "ready"}
curl http://localhost:8001/readyz   # → {"status": "ready"}

# Docker healthcheck status
docker compose ps
# → backend-web-1: Up 21 seconds (healthy)
```

**Production Testing:**
```bash
# Replace with your domain
curl https://yourdomain.com/healthz
curl https://yourdomain.com/readyz
```

## Deployment Instructions

### Local Development

```bash
# Start services
docker compose up -d --build

# Check health
docker compose ps

# View logs (JSON format)
docker compose logs -f web

# Run tests
docker compose exec web pytest -q

# Create backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh ops/backups/nfc_access_2025-10-04_1559.sql.gz
```

### Production Deployment

1. **Pre-deployment:**
   ```bash
   # Review all patches
   ls -la fixes/
   
   # Review security audit
   cat reports/security.txt
   
   # Run tests
   docker compose exec web pytest -q --maxfail=1
   ```

2. **Environment Setup:**
   ```bash
   # Copy production environment template
   cp .env.prod.example .env.prod
   
   # Edit with production values
   nano .env.prod
   ```

3. **Deploy with Docker Compose:**
   ```bash
   # Build and start
   DJANGO_ENV=production docker compose up -d --build
   
   # Run migrations
   docker compose exec web python manage.py migrate
   
   # Collect static files
   docker compose exec web python manage.py collectstatic --noinput
   
   # Create superuser (if needed)
   docker compose exec web python manage.py createsuperuser
   ```

4. **Setup TLS (Nginx):**
   ```bash
   # On production server
   cd /path/to/project/ops/tls
   
   # Edit script with your domain
   nano setup_certbot.sh
   
   # Run setup (as root)
   sudo bash setup_certbot.sh
   ```

5. **Configure Backups:**
   ```bash
   # Add to crontab
   crontab -e
   
   # Daily backup at 2 AM
   0 2 * * * cd /path/to/project && ./scripts/backup.sh >> /var/log/backups.log 2>&1
   ```

6. **Verify Deployment:**
   ```bash
   # Health checks
   curl https://yourdomain.com/healthz
   curl https://yourdomain.com/readyz
   
   # Check logs
   docker compose logs -f web | grep "status.*200"
   
   # Test API
   curl -H "Authorization: Token YOUR_TOKEN" \
        https://yourdomain.com/api/v1/devices/me
   ```

## DoD Checklist

### Security ✓
- [x] Django updated to latest patch version (5.0.14)
- [x] Security audits run (pip-audit, bandit)
- [x] Known vulnerabilities documented
- [x] Default permissions set to `IsAuthenticated`
- [x] Public endpoints explicitly marked
- [x] Docker container runs as non-root user
- [x] TLS configuration prepared (manual setup required)

### Observability ✓
- [x] JSON structured logging implemented
- [x] Request ID tracking enabled
- [x] Access logs capture method, path, status, duration, user
- [x] Health endpoints available (`/health`, `/healthz`)
- [x] Readiness endpoints available (`/ready`, `/readyz`)

### Reliability ✓
- [x] Docker healthcheck configured
- [x] Database backup script with rotation
- [x] Database restore script with safety checks
- [x] Backup automation ready (cron example provided)

### CI/CD ✓
- [x] GitHub Actions workflow created
- [x] Linting configured (ruff, mypy, bandit)
- [x] Security scanning configured (pip-audit, bandit)
- [x] Test suite running in CI
- [x] Coverage reporting enabled
- [x] Docker build ready (commented, awaiting GHCR setup)

### Testing ✓
- [x] All tests passing (51 passed, 1 skipped)
- [x] Code coverage at 67%
- [x] E2E tests documented
- [x] Health checks verified
- [x] Rate limiting verified (existing tests)

### Documentation ✓
- [x] All changes documented in this file
- [x] Deployment instructions provided
- [x] Security audit results documented
- [x] DoD checklist completed
- [x] Patches generated for all changes

## Patches Reference

All changes are available as Git patches in the `fixes/` directory:

1. `fixes/01_security_upgrades.patch` - Django upgrades, pip, security audits
2. `fixes/02_health_endpoints.patch` - /healthz and /readyz aliases
3. `fixes/03_permissions_defaults.patch` - IsAuthenticated by default
4. `fixes/04_json_logging.patch` - Structured logging and middleware
5. `fixes/05_docker_nonroot_and_healthcheck.patch` - Container hardening
6. `fixes/06_nginx_tls_assets.patch` - Nginx config and TLS setup script
7. `fixes/07_db_backup_scripts.patch` - Backup and restore scripts
8. `fixes/08_ci_pipeline.patch` - GitHub Actions CI workflow

## Next Steps

1. **Immediate:**
   - Review security audit results
   - Plan Django upgrade to 5.1+ or 4.2 LTS
   - Test all changes in staging environment

2. **Before Production:**
   - Configure production domain in `ops/tls/setup_certbot.sh`
   - Run TLS setup on production server
   - Configure backup automation (cron)
   - Set up monitoring/alerting for health endpoints

3. **Post-Production:**
   - Monitor JSON logs for anomalies
   - Review coverage reports and improve to 80%+
   - Enable Docker build in CI when GHCR is ready
   - Set up log aggregation (ELK, Splunk, CloudWatch, etc.)

## Support & Maintenance

**Health Check Monitoring:**
```bash
# Add to monitoring system (Prometheus, Datadog, etc.)
GET https://yourdomain.com/healthz  # Should return 200
GET https://yourdomain.com/readyz   # Should return 200
```

**Log Analysis:**
```bash
# View structured logs
docker compose logs web | grep "request_id"

# Find slow requests (>1000ms)
docker compose logs web | jq 'select(.duration_ms > 1000)'

# Find errors
docker compose logs web | jq 'select(.level == "ERROR")'
```

**Backup Management:**
```bash
# List backups
ls -lh ops/backups/

# Test restore in dev environment
./scripts/restore.sh ops/backups/latest.sql.gz

# Verify backup integrity
gunzip -t ops/backups/nfc_access_2025-10-04_1559.sql.gz
```

---

**Generated:** 2025-10-04  
**Project:** OpenWay Access  
**Version:** 1.0.0  
**Status:** ✓ Production Ready (with notes)

