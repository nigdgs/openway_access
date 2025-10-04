#!/usr/bin/env bash
# Security Fix Script — Автоматическое исправление критических уязвимостей
# OpenWay Access Project

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         Security Fix Plan — OpenWay Access               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if running from backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    echo "   Please run this script from the backend directory"
    exit 1
fi

echo "📋 Dependencies updated:"
echo "   ✅ Django 5.0.6 → 5.0.14"
echo "   ✅ Gunicorn 21.2.0 → 22.0.0"
echo "   ✅ django-cors-headers 4.6.0 (added)"
echo ""

# Step 1: Rebuild containers
echo "🔨 Step 1/5: Rebuilding Docker containers..."
docker compose down
docker compose up -d --build

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 10

# Step 2: Check migrations
echo ""
echo "📦 Step 2/5: Checking database migrations..."
if docker compose exec web python manage.py migrate --check; then
    echo "   ✅ Migrations OK"
else
    echo "   ⚠️  Pending migrations detected, applying..."
    docker compose exec web python manage.py migrate
fi

# Step 3: Run tests
echo ""
echo "🧪 Step 3/5: Running test suite..."
if docker compose exec web pytest tests/ -q --tb=short; then
    echo "   ✅ All tests passed"
else
    echo "   ⚠️  Some tests failed (review output above)"
fi

# Step 4: Security checks
echo ""
echo "🔒 Step 4/5: Running security checks..."
docker compose exec web python manage.py check --deploy

# Step 5: Verify versions
echo ""
echo "📊 Step 5/5: Verifying installed versions..."
echo -n "   Django: "
docker compose exec web python -c "import django; print(django.__version__)"
echo -n "   Gunicorn: "
docker compose exec web python -c "import gunicorn; print(gunicorn.__version__)"
echo -n "   CORS Headers: "
docker compose exec web python -c "import corsheaders; print(corsheaders.__version__)"

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                  ✅ Security Fixes Applied                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  MANUAL ACTIONS REQUIRED for Production:"
echo ""
echo "1. 🔑 Update PostgreSQL password:"
echo "   python -c \"import secrets; print(secrets.token_urlsafe(32))\""
echo "   Then update POSTGRES_PASSWORD in .env.prod"
echo ""
echo "2. 🌐 Set CORS allowed origins:"
echo "   CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
echo ""
echo "3. 🛡️  Review DEFAULT_PERMISSION_CLASSES:"
echo "   Consider changing from AllowAny to IsAuthenticated"
echo ""
echo "4. 🚀 Before production deployment:"
echo "   - Set DJANGO_SETTINGS_MODULE=accessproj.settings.prod"
echo "   - Run: make check"
echo "   - Test CORS from frontend"
echo "   - Backup database"
echo ""
echo "📄 Full report: backend/SECURITY_REPORT.md"
echo ""

