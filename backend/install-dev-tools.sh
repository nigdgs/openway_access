#!/usr/bin/env bash
# Установка dev-инструментов в контейнер для статического анализа
set -e

echo "=== Installing development tools ==="

docker compose exec web pip install -r requirements-dev.txt

echo ""
echo "✅ Development tools installed:"
echo "   - black (code formatter)"
echo "   - isort (import sorter)"
echo "   - mypy + django-stubs + djangorestframework-stubs (type checker)"
echo "   - pytest-cov (coverage)"
echo "   - pre-commit (git hooks)"
echo ""
echo "Usage:"
echo "  make check      # Run all checks"
echo "  make format     # Auto-format code"
echo "  make lint-fix   # Auto-fix linting issues"
echo "  make mypy       # Type checking"
echo ""

