# Backend Review - Performance & Observability

**Date:** 2025-10-04  
**Review Type:** Performance Analysis, Caching, N+1 Queries, Server Configuration

---

## Executive Summary

**Overall Performance Rating:** 🟡 **GOOD** (production-ready with optimizations needed)

**Key Findings:**
- ✅ Gunicorn configured with 4 workers
- ✅ DB connection pooling (CONN_MAX_AGE=60)
- ✅ Some query optimization (select_related)
- ⚠️ No caching layer configured
- ⚠️ Potential N+1 queries in access verification
- ⚠️ No metrics/observability endpoints

---

## 1. Application Server Configuration

### Gunicorn Settings (scripts/entrypoint.sh)

```bash
gunicorn accessproj.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

**Analysis:**

| Setting | Value | Assessment | Recommendation |
|---------|-------|------------|----------------|
| Workers | 4 | 🟡 OK for small scale | Scale with CPU: `2 * num_cores + 1` |
| Timeout | 120s | 🟡 High | Reduce to 30-60s; add longer timeout for specific endpoints |
| Worker Class | sync (default) | 🟡 OK | Consider gevent/gthread for I/O-bound workloads |
| Max Requests | None | 🔴 Missing | Add `--max-requests 1000 --max-requests-jitter 50` to prevent memory leaks |
| Keep-Alive | 5s (default) | ✅ OK | |
| Graceful Timeout | 30s (default) | ✅ OK | |

**Recommendations:**

1. **Dynamic Worker Scaling**
   ```bash
   # Calculate workers based on CPU cores
   WORKERS=$((2 * $(nproc) + 1))
   gunicorn --workers $WORKERS ...
   ```

2. **Add Worker Lifecycle**
   ```bash
   --max-requests 1000 \
   --max-requests-jitter 50 \
   --worker-tmp-dir /dev/shm  # Use RAM for worker tmp
   ```

3. **Consider gevent for I/O**
   ```bash
   # If DB/network I/O is bottleneck
   --worker-class gevent \
   --workers 4 \
   --worker-connections 1000
   ```

---

## 2. Database Performance

### Connection Pooling

**Current:** `CONN_MAX_AGE = 60` (seconds)

✅ **GOOD:** Persistent connections reduce connection overhead

**Recommendations:**

1. **Add Connection Timeouts**
   ```python
   DATABASES = {
       "default": {
           ...
           "CONN_MAX_AGE": 60,
           "OPTIONS": {
               "connect_timeout": 5,
               "options": "-c statement_timeout=30000"  # 30s
           }
       }
   }
   ```

2. **Monitor Connection Pool**
   - Add pg_stat_activity monitoring
   - Track idle connections
   - Set max_connections appropriately

### Query Optimization

**Findings:**

✅ **GOOD:** select_related used in critical path
```python
# apps/api/v1/views.py:95
token_obj = Token.objects.select_related("user").filter(key=token).first()
```

⚠️ **POTENTIAL N+1:** User groups lookup
```python
# apps/api/v1/views.py:110
Q(access_point=ap, group__in=user.groups.all(), allow=True)
```

**Impact Analysis:**

| Query | Current | Queries | Improvement |
|-------|---------|---------|-------------|
| Token lookup | `select_related("user")` | 2 | ✅ Already optimized |
| Permission check | No prefetch | 2-3 | ⚠️ Could prefetch groups |
| Access event create | Single insert | 1 | ✅ OK |
| Device list | No select_related | N+1 | 🔴 Needs optimization |

**Recommendations:**

1. **Optimize Permission Check**
   ```python
   # apps/api/v1/views.py
   from django.contrib.auth.models import User
   
   # Prefetch groups for user
   token_obj = Token.objects.select_related("user").prefetch_related("user__groups").filter(key=token).first()
   ```

2. **Optimize Device List**
   ```python
   # apps/api/v1/views.py:190
   devices = Device.objects.filter(user=request.user).select_related("user").order_by("-created_at")
   ```

3. **Add Query Debugging**
   ```python
   # settings/dev.py
   LOGGING = {
       'loggers': {
           'django.db.backends': {
               'level': 'DEBUG',
               'handlers': ['console'],
           }
       }
   }
   ```

---

## 3. Caching Strategy

### Current State: ❌ **NO CACHING CONFIGURED**

**Analysis:**

- ✅ Test environment has LocMemCache (for throttling tests)
- ❌ Dev/Prod have no CACHES configuration
- ❌ No Redis/Memcached integration
- ⚠️ Rate limiting falls back to default (memory, loses state on restart)

**Impact:**

1. **Rate Limiting:** In-process memory → lost on restarts
2. **Token Lookups:** No caching → DB hit every request
3. **Permission Checks:** No caching → DB queries every verify
4. **Session Storage:** Uses DB by default → slow

**Recommendations:**

### Step 1: Add Redis

```yaml
# compose.yml
services:
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Step 2: Configure Django Cache

```python
# settings/prod.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.environ.get('REDIS_HOST', 'redis')}:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "openway",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

# Use Redis for sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

### Step 3: Cache Token Lookups

```python
# apps/api/v1/views.py
from django.core.cache import cache

def get_user_from_token(token_key):
    # Try cache first
    cache_key = f"token:{token_key}"
    user_id = cache.get(cache_key)
    
    if user_id:
        return User.objects.get(id=user_id)
    
    # Cache miss - query DB
    token_obj = Token.objects.select_related("user").filter(key=token_key).first()
    if token_obj and token_obj.user.is_active:
        cache.set(cache_key, token_obj.user.id, timeout=300)  # 5 min
        return token_obj.user
    
    return None
```

### Step 4: Cache Permission Checks

```python
def check_user_access(user, access_point_id):
    cache_key = f"perm:{user.id}:{access_point_id}"
    result = cache.get(cache_key)
    
    if result is not None:
        return result
    
    # Query permissions
    has_perm = AccessPermission.objects.filter(
        Q(access_point_id=access_point_id, user=user, allow=True) |
        Q(access_point_id=access_point_id, group__in=user.groups.all(), allow=True)
    ).exists()
    
    cache.set(cache_key, has_perm, timeout=60)  # 1 min (short TTL for security)
    return has_perm
```

**Cache Invalidation Strategy:**

```python
# apps/access/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=AccessPermission)
def invalidate_permission_cache(sender, instance, **kwargs):
    # Clear all permission caches for affected user/group
    if instance.user:
        cache.delete_pattern(f"perm:{instance.user.id}:*")
    if instance.group:
        for user in instance.group.user_set.all():
            cache.delete_pattern(f"perm:{user.id}:*")
```

---

## 4. Observability & Monitoring

### Current State: ⚠️ **BASIC LOGGING ONLY**

**What Exists:**
- ✅ Health checks: /healthz, /readyz
- ✅ JSON logging configured (logging_json.py)
- ✅ Custom middleware (RequestIdMiddleware, AccessLogMiddleware)
- ✅ Access event logging (AccessEvent model)

**What's Missing:**
- ❌ Prometheus /metrics endpoint
- ❌ APM integration (Sentry, DataDog, etc.)
- ❌ Slow query logging
- ❌ Request duration tracking
- ❌ Database connection pool metrics
- ❌ Cache hit/miss metrics

### Recommendations:

#### 1. Add Prometheus Metrics

```bash
# requirements.txt
django-prometheus==2.3.1
```

```python
# settings/prod.py
INSTALLED_APPS = [
    'django_prometheus',
    ...
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Use instrumented DB backend
DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        ...
    }
}

# Use instrumented cache
CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        ...
    }
}
```

```python
# core/urls.py
from django.urls import path
from django_prometheus import exports

urlpatterns = [
    ...
    path("metrics", exports.ExportToDjangoView, name="metrics"),
]
```

**Metrics Exposed:**
- `django_http_requests_total` - Request count by method/status
- `django_http_requests_latency_seconds` - Request duration histogram
- `django_db_query_duration_seconds` - Query duration
- `django_cache_get_total` - Cache operations
- `gunicorn_workers` - Worker count

#### 2. Add Sentry for Error Tracking

```bash
# requirements.txt
sentry-sdk[django]==2.0.0
```

```python
# settings/prod.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,  # 10% performance monitoring
    profiles_sample_rate=0.1,
    environment=os.environ.get("ENVIRONMENT", "production"),
)
```

#### 3. Add Request Duration Middleware

```python
# core/middleware.py
import time
import logging

logger = logging.getLogger("django.request")

class RequestDurationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log slow requests
        if duration_ms > 1000:  # > 1 second
            logger.warning(
                f"Slow request: {request.method} {request.path} took {duration_ms:.0f}ms",
                extra={
                    "duration_ms": duration_ms,
                    "method": request.method,
                    "path": request.path,
                }
            )
        
        # Add header
        response["X-Response-Time"] = f"{duration_ms:.0f}"
        return response
```

---

## 5. Load Testing Recommendations

### Critical Endpoints to Test:

1. **POST /api/v1/access/verify** (highest QPS expected)
   - Target: 30 req/sec per gate
   - Load test with 100 concurrent users
   - Validate rate limiting works

2. **POST /api/v1/auth/token**
   - Typical: 1-5 req/sec
   - Load test authentication throughput

3. **POST /api/v1/devices/register**
   - Typical: 0.1-1 req/sec
   - Test token generation under load

### Sample Load Test (Locust)

```python
# locustfile.py
from locust import HttpUser, task, between

class AccessVerifyUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        # Login and get token
        response = self.client.post("/api/v1/auth/token", json={
            "username": "demo",
            "password": "StrongPass_123"
        })
        self.token = response.json()["token"]
    
    @task(10)
    def verify_access(self):
        self.client.post("/api/v1/access/verify", json={
            "gate_id": "GATE_001",
            "token": self.token
        })
    
    @task(1)
    def list_devices(self):
        self.client.get("/api/v1/devices/me", headers={
            "Authorization": f"Token {self.token}"
        })
```

**Run:**
```bash
locust -f locustfile.py --host http://localhost:8001
# Open http://localhost:8089 and start test
```

---

## 6. Performance Benchmarks (Estimated)

### Current Architecture (No Cache)

| Endpoint | Avg Latency | p95 | p99 | Throughput |
|----------|-------------|-----|-----|------------|
| /healthz | 5ms | 10ms | 15ms | 1000+ req/s |
| /readyz | 50ms | 100ms | 200ms | 100 req/s |
| POST /api/v1/access/verify | 100ms | 200ms | 500ms | 30 req/s* |
| POST /api/v1/auth/token | 200ms | 400ms | 800ms | 10 req/s |
| POST /api/v1/devices/register | 150ms | 300ms | 600ms | 20 req/s |

*\* Rate limited to 30/second*

### With Redis Caching (Projected)

| Endpoint | Avg Latency | p95 | p99 | Throughput |
|----------|-------------|-----|-----|------------|
| POST /api/v1/access/verify | **20ms** ⬇️ | 50ms | 100ms | 100+ req/s |
| POST /api/v1/auth/token | **100ms** ⬇️ | 200ms | 400ms | 20 req/s |

**Expected Improvements:**
- 5x reduction in access verify latency (cache hit)
- 3x increase in sustainable throughput
- Reduced DB load by 70-80%

---

## Summary of Recommendations

### 🔴 HIGH PRIORITY (Before Production Scale)

1. **Add Redis for caching**
   - Caches: tokens, permissions, sessions
   - Rate limiting state
   - Expected ROI: 5x latency reduction

2. **Optimize N+1 queries**
   - Add prefetch_related for user.groups
   - Add select_related for device list
   - Expected ROI: 30% latency reduction

3. **Add Prometheus metrics**
   - Enable observability
   - Track performance degradation
   - Alert on SLA violations

### 🟡 MEDIUM PRIORITY (First Month)

4. **Tune Gunicorn**
   - Dynamic worker count
   - Add max-requests for memory
   - Consider gevent for I/O

5. **Add Sentry**
   - Error tracking
   - Performance monitoring
   - User feedback loop

6. **Implement slow query logging**
   - Identify bottlenecks
   - Optimize indexes
   - Query plan analysis

### 🟢 LOW PRIORITY (3-6 Months)

7. **Load testing**
   - Establish baselines
   - Capacity planning
   - Stress testing

8. **DB Read Replicas**
   - Scale read-heavy workloads
   - Analytics separation
   - Reduce primary load

9. **CDN for static assets**
   - Offload static serving
   - Reduce bandwidth costs
   - Global distribution

---

**Status:** COMPLETED - Performance reviewed  
**Critical:** 3 (caching, N+1, metrics)  
**Medium:** 3 (gunicorn, APM, logging)  
**Overall:** 🟡 Good foundation, needs caching layer for production scale

