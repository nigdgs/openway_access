# Backend Review - Database & Migrations

**Date:** 2025-10-04  
**Review Type:** Database Schema, Migrations, Indexes Analysis

---

## Migration Status

### All Migrations Applied ✓

```
access
 [X] 0001_initial
 [X] 0002_accesspermission_access_acce_access__9a3b45_idx_and_more

accounts
 [X] 0001_initial

devices
 [X] 0001_initial
 [X] 0002_auto_20250912_1225
 [X] 0003_alter_device_totp_secret

+ Django core migrations (admin, auth, authtoken, contenttypes, sessions)
```

✅ **makemigrations --check:** No pending changes detected

---

## Schema Analysis

### 1. **accounts_passwordhistory**

**Purpose:** Store password history for preventing reuse

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | bigint | PK | Auto-generated |
| password | varchar(255) | NOT NULL | Stores hash |
| created_at | timestamptz | NOT NULL | Auto-added |
| user_id | integer | FK → auth_user | NOT NULL |

**Indexes:**
- ✓ Primary key on `id`
- ✓ Index on `user_id` (FK lookup)

**Assessment:** ✅ Good - supports password validation efficiently

---

### 2. **devices_device**

**Purpose:** User devices (Android/iOS) with static auth tokens

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | bigint | PK | Auto-generated |
| user_id | integer | FK → auth_user | NOT NULL |
| name | varchar(100) | | Optional |
| android_device_id | varchar(128) | NULL | Optional |
| totp_secret | varchar(64) | | Legacy (future use) |
| auth_token | varchar(64) | UNIQUE | Static token |
| is_active | boolean | NOT NULL | Default True |
| created_at | timestamptz | NOT NULL | Auto-added |

**Indexes:**
- ✓ Primary key on `id`
- ✓ **UNIQUE** on `auth_token` (critical for lookups)
- ✓ Index on `auth_token` with `varchar_pattern_ops` (LIKE queries)
- ✓ Index on `user_id` (FK lookup)

**Assessment:** ✅ Excellent - unique constraint and pattern ops for fast token lookups

---

### 3. **access_accesspoint**

**Purpose:** Physical access points (gates, doors)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | bigint | PK | Auto-generated |
| code | varchar(64) | UNIQUE | Gate identifier |
| name | varchar(128) | | Human-readable |
| location | varchar(128) | | Optional |

**Indexes:**
- ✓ Primary key on `id`
- ✓ **UNIQUE** on `code` (gate_id lookups)
- ✓ Index on `code` with `varchar_pattern_ops`

**Assessment:** ✅ Excellent - unique code enables fast gate verification

---

### 4. **access_accesspermission**

**Purpose:** RBAC permissions (user or group → access point)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | bigint | PK | Auto-generated |
| access_point_id | bigint | FK → AccessPoint | NOT NULL |
| user_id | integer | FK → auth_user | NULL |
| group_id | integer | FK → auth_group | NULL |
| allow | boolean | NOT NULL | Default True |

**Constraints:**
- ✅ Check: `user_id IS NOT NULL OR group_id IS NOT NULL`
- ✅ Unique: `(access_point_id, user_id, group_id)`

**Indexes:**
- ✓ Primary key on `id`
- ✓ **Composite:** `(access_point_id, user_id)` → Critical for user checks
- ✓ **Composite:** `(access_point_id, group_id)` → Critical for group checks
- ✓ Index on `access_point_id`
- ✓ Index on `group_id`
- ✓ Index on `user_id`

**Assessment:** ✅ Excellent - optimal indexing for RBAC queries

**Query Performance:**
```sql
-- Fast: Composite index hits
SELECT * FROM access_accesspermission 
WHERE access_point_id = 1 AND user_id = 5;

-- Fast: Composite index hits
SELECT * FROM access_accesspermission 
WHERE access_point_id = 1 AND group_id = 2;
```

---

### 5. **access_accessevent** ⚠️

**Purpose:** Audit log of all access attempts

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | bigint | PK | Auto-generated |
| access_point_id | bigint | FK → AccessPoint | NULL (SET_NULL) |
| user_id | integer | FK → auth_user | NULL (SET_NULL) |
| device_id | integer | | NULL (not FK!) |
| decision | varchar(10) | NOT NULL | ALLOW/DENY |
| reason | varchar(64) | | OK, NO_PERMISSION, etc. |
| raw | jsonb | NULL | Full request data |
| created_at | timestamptz | NOT NULL | Timestamp |

**Indexes:**
- ✓ Primary key on `id`
- ✓ Index on `access_point_id`
- ✓ Index on `user_id`
- ⚠️ **MISSING:** Index on `created_at`
- ⚠️ **MISSING:** Composite index on `(created_at, decision)`

**Current Record Count:** 6 (demo data)

**Assessment:** 🟡 **CRITICAL GAP - Missing temporal indexes**

---

## 🔴 Critical Issues

### Issue #1: Missing Index on `access_accessevent.created_at`

**Impact:**
- Slow purge operations (delete old records)
- Poor analytics query performance
- Table scans for time-based queries
- Becomes critical at scale (1M+ records)

**Evidence:**
```sql
-- Current implementation (slow at scale)
DELETE FROM access_accessevent 
WHERE created_at < NOW() - INTERVAL '90 days';
-- → Full table scan without index on created_at
```

**Queries Affected:**
- Purge old events (management command)
- Audit reports by date range
- Dashboard statistics (recent activity)
- Compliance exports (time-based filtering)

**Recommendation:**
```python
# Add to access/models.py AccessEvent.Meta
indexes = [
    models.Index(fields=['-created_at']),  # DESC for recent-first queries
    models.Index(fields=['created_at', 'decision']),  # Analytics
]
```

**Migration:**
```bash
# Create migration
docker compose exec web python manage.py makemigrations access \
  --name add_accessevent_temporal_indexes

# Review and apply
docker compose exec web python manage.py migrate
```

---

## 🟡 Medium Priority Issues

### Issue #2: `device_id` Not a Foreign Key

**Current:**
```python
device_id = models.IntegerField(null=True, blank=True)
```

**Problem:**
- No referential integrity
- Can reference non-existent devices
- No CASCADE behavior on device deletion

**Recommendation:**
```python
device = models.ForeignKey(
    'devices.Device',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='access_events'
)
```

**Impact:** Data integrity, easier analytics via JOINs

---

### Issue #3: No Composite Index for Analytics

**Common Query Pattern:**
```python
# Dashboard: Recent DENY events
AccessEvent.objects.filter(
    decision='DENY',
    created_at__gte=last_24h
).order_by('-created_at')
```

**Recommendation:**
```python
models.Index(fields=['decision', '-created_at'])
```

---

## ✅ Good Practices

1. **Connection Pooling:** `CONN_MAX_AGE=60` configured
2. **Foreign Keys:** Proper CASCADE and SET_NULL strategies
3. **Unique Constraints:** Enforced at DB level (auth_token, gate code)
4. **Check Constraints:** Business logic enforced (user XOR group)
5. **Composite Indexes:** Optimized for access check queries
6. **Pattern Ops Indexes:** Support LIKE queries on tokens
7. **JSONb Type:** Efficient storage for raw request data

---

## Index Usage Analysis

### Most Critical (High QPS):

**access_accesspermission composite indexes:**
- Used on every `/api/v1/access/verify` call
- Estimated QPS: 10-100 per second (real-world deployment)
- Current: ✅ Optimal

**devices_device.auth_token unique:**
- Used on device auth lookups (future feature)
- Current: ✅ Optimal

**access_accesspoint.code unique:**
- Used on every gate verification
- Current: ✅ Optimal

### Audit/Analytics (Low QPS, Large Scans):

**access_accessevent temporal queries:**
- Purge operations: Daily/weekly batch jobs
- Analytics: Ad-hoc queries, dashboards
- Current: ⚠️ Missing indexes

---

## Database Statistics

**PostgreSQL Version:** 16-alpine  
**Encoding:** UTF8  
**Locale:** Default (consider setting to C for performance)

**Connection Settings:**
```python
CONN_MAX_AGE = 60  # Good for web workloads
# Consider adding:
# 'OPTIONS': {
#     'connect_timeout': 5,
#     'options': '-c statement_timeout=30000'  # 30s
# }
```

---

## Recommendations Summary

### Immediate (Before Production):
1. 🔴 Add index on `access_accessevent.created_at`
2. 🟡 Add composite index `(decision, created_at)` for analytics
3. 🟡 Consider converting `device_id` to ForeignKey

### Short-term (First Month):
4. Monitor slow query log (enable `log_min_duration_statement = 500`)
5. Set up pg_stat_statements extension
6. Implement partitioning for `access_accessevent` (by month/year)
7. Add `statement_timeout` to prevent runaway queries

### Long-term (3-6 Months):
8. Evaluate read replicas for analytics
9. Consider TimescaleDB for event time-series data
10. Implement automated VACUUM scheduling
11. Set up Prometheus postgres_exporter for metrics

---

## Migration Plan

### Step 1: Create Migration

```bash
cd backend
docker compose exec web python manage.py makemigrations access \
  --name optimize_accessevent_indexes --empty
```

### Step 2: Edit Migration

```python
# apps/access/migrations/00XX_optimize_accessevent_indexes.py
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

### Step 3: Test & Apply

```bash
# Dry run
docker compose exec web python manage.py migrate access --plan

# Apply
docker compose exec web python manage.py migrate access

# Verify
docker compose exec db psql -U nfc -d nfc_access \
  -c "\d+ access_accessevent"
```

---

## Compliance Notes

- ✅ Audit trail (AccessEvent) captures all access attempts
- ✅ Retention policy implemented (purge management command)
- ⚠️ Consider encryption at rest for sensitive JSONB data
- ⚠️ GDPR: Ensure CASCADE DELETE for user data removal

---

**Status:** COMPLETED - Database schema reviewed  
**Critical Issues:** 1 (missing temporal index)  
**Medium Issues:** 2 (FK integrity, analytics index)  
**Overall Assessment:** 🟡 Good foundation, needs index optimization before scale

