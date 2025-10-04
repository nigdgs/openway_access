# Backend Review Fixes

**Date:** 2025-10-04  
**Review Branch:** feature/backend-review  
**Base Commit:** ecbd4469341d0e3c823541ad022fb3e35621285a

---

## Overview

This directory contains proposed patches and fixes identified during the comprehensive backend review. Each fix addresses specific issues found in dependencies, security, database, code quality, or performance.

---

## Priority Levels

- 🔴 **CRITICAL** - Must fix before production
- 🟡 **HIGH** - Fix in first sprint after launch
- 🟢 **MEDIUM** - Fix in first month

---

## Proposed Fixes

### 🔴 Fix #1: Django Security Upgrade

**File:** `backend_django_upgrade.diff`  
**Priority:** CRITICAL  
**Effort:** 1 hour  
**Risk:** Low (LTS → LTS upgrade)

**Issue:**
- Django 5.0.14 has 2 CVEs:
  - CVE-2025-48432: Log injection via request.path
  - CVE-2025-57833: SQL injection in FilteredRelation

**Solution:**
```diff
--- requirements.txt
+++ requirements.txt
-Django~=5.0.14
+Django~=5.2.7
-djangorestframework==3.15.2
+djangorestframework==3.16.1
```

**Testing:**
```bash
cd backend
pip install -r requirements.txt
pytest --cov
python manage.py check --deploy
docker compose up --build
```

**Rollback:** Revert requirements.txt, rebuild

---

### 🔴 Fix #2: Database Index Optimization

**File:** `backend_db_indexes.py` (migration file)  
**Priority:** CRITICAL  
**Effort:** 30 minutes  
**Risk:** Low (additive migration)

**Issue:**
- AccessEvent table lacks index on `created_at`
- Purge operations will be slow at scale (1M+ records)
- Analytics queries scan entire table

**Solution:**
Create migration file in `apps/access/migrations/`:

```python
# 0003_optimize_accessevent_indexes.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('access', '0002_accesspermission_access_acce_access__9a3b45_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='accessevent',
            index=models.Index(
                fields=['-created_at'],
                name='access_event_created_desc_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='accessevent',
            index=models.Index(
                fields=['decision', '-created_at'],
                name='access_event_decision_time_idx'
            ),
        ),
    ]
```

**Testing:**
```bash
# Apply migration
docker compose exec web python manage.py migrate

# Verify indexes
docker compose exec db psql -U nfc -d nfc_access \
  -c "\d+ access_accessevent"

# Test purge performance
docker compose exec web python manage.py purge_access_events --days 90
```

**Rollback:** Create reverse migration or `DROP INDEX`

---

### 🔴 Fix #3: Strong Database Password

**File:** `backend_env_security.sh` (helper script)  
**Priority:** CRITICAL  
**Effort:** 5 minutes  
**Risk:** Medium (requires restart)

**Issue:**
- Current password: `POSTGRES_PASSWORD=nfc` (trivial)
- Easy to brute force or guess
- Production security risk

**Solution:**
```bash
#!/bin/bash
# Generate strong password
NEW_PASSWORD=$(openssl rand -hex 32)

# Update .env
sed -i.bak "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASSWORD/" .env

echo "✅ New password set: ${NEW_PASSWORD:0:8}...${NEW_PASSWORD: -8}"
echo "⚠️  Restart containers: docker compose down && docker compose up -d"
```

**Testing:**
```bash
# After restart, verify connection
docker compose exec web python manage.py check
```

**Rollback:** Restore .env.bak, restart

---

### 🔴 Fix #4: Password Validator Tests

**File:** `backend_password_validator_tests.py`  
**Priority:** CRITICAL  
**Effort:** 2 hours  
**Risk:** Low (test-only change)

**Issue:**
- apps/accounts/validators.py has 0% test coverage
- RecentPasswordValidator may fail silently
- Security feature not validated

**Solution:**
Create test file in `tests/`:

```python
# test_password_validator.py
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.accounts.validators import RecentPasswordValidator

User = get_user_model()

@pytest.mark.django_db
class TestRecentPasswordValidator:
    def test_rejects_recent_password(self):
        user = User.objects.create_user(username="test", password="Pass1!")
        validator = RecentPasswordValidator(history_size=3)
        
        # Change password twice
        user.set_password("Pass2!")
        user.save()
        user.set_password("Pass3!")
        user.save()
        
        # Try to reuse first password
        with pytest.raises(ValidationError, match="recently used"):
            validator.validate("Pass1!", user)
    
    def test_allows_old_password_after_history_limit(self):
        user = User.objects.create_user(username="test", password="Pass1!")
        validator = RecentPasswordValidator(history_size=2)
        
        # Change password 3 times (exceeds history)
        for i in range(2, 5):
            user.set_password(f"Pass{i}!")
            user.save()
        
        # First password should now be allowed
        validator.validate("Pass1!", user)  # Should not raise
    
    def test_allows_unique_password(self):
        user = User.objects.create_user(username="test", password="Pass1!")
        validator = RecentPasswordValidator()
        
        # New unique password should pass
        validator.validate("BrandNewPass123!", user)
```

**Testing:**
```bash
pytest tests/test_password_validator.py -v
```

**Impact:** Ensures password security policy works correctly

---

### 🟡 Fix #5: Add Redis Caching

**File:** `backend_redis_integration.diff`  
**Priority:** HIGH  
**Effort:** 4 hours  
**Risk:** Medium (new dependency)

**Issue:**
- No caching layer configured
- Token lookups hit DB every request
- Limited to 30 req/s due to DB bottleneck

**Solution:**

1. Update compose.yml:
```yaml
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  redis_data:
```

2. Update requirements.txt:
```txt
django-redis==5.4.0
```

3. Update settings/prod.py:
```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "openway",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
```

**Testing:**
```bash
# Start Redis
docker compose up -d redis

# Verify connection
docker compose exec web python -c "from django.core.cache import cache; cache.set('test', 1); print(cache.get('test'))"

# Load test
locust -f tests/load_test.py --host http://localhost:8001
```

**Expected Impact:**
- 5x latency reduction (100ms → 20ms)
- 3x throughput increase (30 req/s → 100+ req/s)

**Rollback:** Remove redis from compose, revert settings

---

### 🟡 Fix #6: Code Style Auto-Fix

**File:** `backend_code_style.sh`  
**Priority:** LOW  
**Effort:** 5 minutes  
**Risk:** None (formatting only)

**Issue:**
- 11 ruff violations (imports, whitespace, modernization)
- Code inconsistency

**Solution:**
```bash
#!/bin/bash
cd backend
docker compose exec web ruff check --fix .
docker compose exec web ruff format .
```

**Changes:**
- Sort imports (I001)
- Remove trailing whitespace (W293)
- Move imports to top (E402)
- Use datetime.UTC (UP017)

**Testing:**
```bash
docker compose exec web ruff check .
# Should report: All checks passed!
```

**Rollback:** Git revert (cosmetic changes only)

---

## Application Instructions

### Option A: Apply All Critical Fixes (Recommended)

```bash
# 1. Upgrade dependencies
cd /Users/aleksandr/Developer/openway_access/backend
vim requirements.txt  # Update Django to 5.2.7
pip install -r requirements.txt

# 2. Create DB index migration
docker compose exec web python manage.py makemigrations access \
  --name optimize_accessevent_indexes --empty
# Edit migration file (see Fix #2)
docker compose exec web python manage.py migrate

# 3. Generate strong DB password
openssl rand -hex 32
vim .env  # Update POSTGRES_PASSWORD
docker compose down && docker compose up -d

# 4. Add password validator tests
# Create tests/test_password_validator.py (see Fix #4)
pytest tests/test_password_validator.py

# 5. Run full test suite
pytest --cov --cov-report=term-missing

# 6. Deploy
docker compose up --build -d
```

### Option B: Apply Selectively

Choose fixes based on priority and schedule. Each fix is independent except:
- Fix #5 (Redis) should be applied with app code changes for caching

---

## Verification Checklist

After applying fixes, verify:

- [ ] All tests pass: `pytest`
- [ ] Security check passes: `manage.py check --deploy`
- [ ] No new CVEs: `pip-audit`
- [ ] Migrations applied: `manage.py showmigrations`
- [ ] Services healthy: `docker compose ps`
- [ ] API responds: `curl http://localhost:8001/healthz`
- [ ] Performance improved (if Redis added)

---

## Support

For questions or issues with these fixes, refer to:
- **Main Report:** `docs/backend_review_summary.md`
- **Detailed Reports:** `reports/backend_*.txt|md`
- **Git Branch:** feature/backend-review
- **Contact:** Senior Backend/SEC Reviewer

---

**Review Date:** 2025-10-04  
**Status:** Pending Team Review  
**Next Step:** Prioritize and schedule fixes

