
# Backend (Django + DRF) — каркас

## Быстрый старт (dev)
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Отредактируйте .env при необходимости
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```
Для Docker см. `infra/docker-compose.yml` на уровень выше.

## Полезные урлы
- `/admin/` — админка
- `/schema/` — OpenAPI схема
- `/api/mobile/ticket` — выдача краткого ключа
- `/api/access/verify` — проверка допуска
- `/api/events` — журналы
- `/api/controllers/config` — конфиг для офлайна
