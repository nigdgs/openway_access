# Backend Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VIRTUALENVS_CREATE=false

# System deps (psycopg2 build & runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements if present; otherwise install sane defaults
COPY requirements.txt* /app/
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    else \
      pip install --no-cache-dir django==5.* djangorestframework psycopg2-binary gunicorn; \
    fi

# Copy project
COPY . /app

EXPOSE 8000

# Default command is a no-op so Codex can run custom commands (migrate/run/test)
CMD ["bash","-lc","sleep infinity"]
