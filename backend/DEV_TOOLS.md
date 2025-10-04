# Development Tools Guide

## Установка

```bash
# В контейнере (рекомендуется)
./install-dev-tools.sh

# Или локально
pip install -r requirements-dev.txt
```

## Быстрый старт

```bash
make help         # Показать все доступные команды
make check        # Запустить все проверки (ruff + mypy + black + isort)
make format       # Автоформатирование (black + isort)
make lint-fix     # Автофикс линтера (ruff --fix)
```

## Инструменты

### 1. **Ruff** — Быстрый линтер (заменяет flake8 + pylint)

```bash
make lint         # Проверка без изменений
make lint-fix     # Автофикс нарушений
```

**Конфиг:** `pyproject.toml` → `[tool.ruff]`  
**Правила:** E, F, W, I, N, UP, S, B, C4, DTZ

### 2. **Black** — Автоформатирование кода

```bash
make black        # Проверка форматирования
make black-fix    # Автоформатирование
```

**Конфиг:** `pyproject.toml` → `[tool.black]`  
**Line length:** 120 символов

### 3. **isort** — Сортировка импортов

```bash
make isort        # Проверка порядка импортов
make isort-fix    # Автосортировка
```

**Конфиг:** `pyproject.toml` → `[tool.isort]`  
**Profile:** black-compatible

### 4. **mypy** — Статическая проверка типов

```bash
make mypy         # Проверка типизации
```

**Конфиг:** `pyproject.toml` → `[tool.mypy]`  
**Plugins:** django-stubs, djangorestframework-stubs

### 5. **pre-commit** — Git hooks (опционально)

```bash
# Установка hooks
docker compose exec web pre-commit install

# Проверка всех файлов
docker compose exec web pre-commit run --all-files
```

**Конфиг:** `.pre-commit-config.yaml`

## Workflow

### Перед коммитом

```bash
make format       # 1. Форматирование
make check        # 2. Проверка всех правил
make test         # 3. Запуск тестов
```

### CI/CD Pipeline (рекомендуется)

```yaml
# .github/workflows/ci.yml
- name: Lint
  run: make lint

- name: Type check
  run: make mypy

- name: Format check
  run: make black && make isort

- name: Tests
  run: make test
```

## Исправление типичных ошибок

### 1. Mypy: "missing library stubs"
**Решено:** Установлены `django-stubs` и `djangorestframework-stubs`

### 2. Black: "would reformat"
```bash
make black-fix  # Автоформатирование
```

### 3. isort: "imports are incorrectly sorted"
```bash
make isort-fix  # Автосортировка
```

### 4. Ruff: "line too long"
```bash
make lint-fix   # Автофикс (где возможно)
# Или вручную разбить длинную строку
```

## Игнорирование правил

### Для всего файла (в `pyproject.toml`)
```toml
[tool.ruff.lint.per-file-ignores]
"scripts/**.py" = ["E402"]  # отключить E402 для scripts/
```

### Для одной строки (в коде)
```python
result = some_function()  # noqa: F841
```

### Для блока (mypy)
```python
# type: ignore[import-untyped]
```

## Статистика проекта

```bash
# Подсчёт строк кода
docker compose exec web sh -c "find . -name '*.py' -not -path '*/migrations/*' | xargs wc -l | tail -1"

# Coverage отчёт
docker compose exec web pytest --cov=apps --cov-report=html
# Откроется в htmlcov/index.html
```

## Troubleshooting

### "Module not found" в mypy
→ Добавить в `requirements-dev.txt` типы: `types-<package>`

### Ruff vs Black конфликты
→ Используем `profile = "black"` в isort — конфликтов нет

### Pre-commit медленный
→ Использовать `--hook-stage manual` для тяжёлых хуков

## Дополнительные инструменты (опционально)

- **bandit** — проверка безопасности (уже покрыто ruff S-правилами)
- **radon** — метрики сложности кода
- **interrogate** — проверка docstrings
- **coverage** — анализ покрытия тестами (pytest-cov)

---

**Автор:** OpenWay Access Team  
**Обновлено:** 2025-10-04

