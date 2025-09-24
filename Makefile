SHELL := /bin/bash
PYTHON := $(PWD)/.venv/bin/python
PIP := $(PWD)/.venv/bin/pip
BANDIT := $(PWD)/.venv/bin/bandit
RUFF := $(PWD)/.venv/bin/ruff
BLACK := $(PWD)/.venv/bin/black
ISORT := $(PWD)/.venv/bin/isort
MYPY := $(PWD)/.venv/bin/mypy
COVERAGE := $(PWD)/.venv/bin/coverage
DJANGO_SETTINGS ?= accessproj.settings.dev

.PHONY: venv deps dev test lint fmt fmt-check up down loadtest coverage report clean

venv:
	@test -d .venv || python3 -m venv .venv
	$(PIP) install --upgrade pip

deps:
	$(PIP) install -r backend/requirements.txt
	$(PIP) install -r backend/requirements-dev.txt

migrate:
	$(PYTHON) backend/manage.py migrate --settings=$(DJANGO_SETTINGS)

superuser:
	$(PYTHON) backend/manage.py createsuperuser --settings=$(DJANGO_SETTINGS)

shell:
	$(PYTHON) backend/manage.py shell --settings=$(DJANGO_SETTINGS)

runserver:
	$(PYTHON) backend/manage.py runserver 0.0.0.0:8000 --settings=$(DJANGO_SETTINGS)

dev: venv deps migrate runserver

test:
	$(COVERAGE) run --rcfile=coverage.ini backend/manage.py test --settings=accessproj.settings.test
	$(COVERAGE) xml -o coverage.xml
	$(COVERAGE) report

lint:
	$(RUFF) check backend
	$(BLACK) --check backend
	$(ISORT) --check-only backend
	$(MYPY) backend/apps backend/core backend/accessproj
	$(BANDIT) -q -r backend/apps

fmt:
	$(ISORT) backend
	$(BLACK) backend

fmt-check:
	$(ISORT) --check-only backend
	$(BLACK) --check backend

up:
	docker compose -f backend/compose.yml --env-file .env up -d

logs:
	docker compose -f backend/compose.yml --env-file .env logs -f web

down:
	docker compose -f backend/compose.yml --env-file .env down

loadtest:
	k6 run perf/k6_verify.js

report:
	$(COVERAGE) html

clean:
	rm -f coverage.xml
	rm -rf htmlcov
