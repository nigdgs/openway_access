FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl netcat-traditional postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
    pip install --default-timeout=300 --no-cache-dir -r requirements.txt

COPY . /app/
RUN chmod +x scripts/*.sh

# Create non-root user
RUN groupadd -g 1000 app && \
    useradd -u 1000 -g app -s /bin/bash -m app && \
    chown -R app:app /app

USER 1000:1000

EXPOSE 8000
# dev server for MVP
CMD ["bash", "-lc", "./scripts/entrypoint.sh"]