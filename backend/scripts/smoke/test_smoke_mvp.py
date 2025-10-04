#!/usr/bin/env python
"""Smoke-тест MVP через Django shell"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "accessproj.settings.dev")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.access.models import AccessPermission, AccessPoint

User = get_user_model()

print("\n" + "="*60)
print("SMOKE TEST: POST /api/v1/access/verify (MVP + RBAC)")
print("="*60)

# Создаём тестового пользователя
user, created = User.objects.get_or_create(
    username="smokeuser",
    defaults={"is_active": True}
)
if created:
    user.set_password("pass123")
    user.save()
    print(f"✓ Создан пользователь: {user.username}")
else:
    print(f"✓ Используется существующий пользователь: {user.username}")

# Создаём токен
token, created = Token.objects.get_or_create(user=user)
print(f"✓ User token: {token.key[:16]}...{token.key[-16:]}")

# Создаём gate
gate, created = AccessPoint.objects.get_or_create(
    code="smoke-gate-01",
    defaults={"name": "Smoke Test Gate"}
)
print(f"✓ Gate: {gate.code}")

# RBAC: Даём разрешение пользователю (Вариант 1)
perm, created = AccessPermission.objects.get_or_create(
    access_point=gate,
    user=user,
    defaults={"allow": True}
)
if created:
    print("✓ Создано разрешение AccessPermission для пользователя")
else:
    print("✓ Используется существующее разрешение")

# API Client
client = APIClient()
url = "/api/v1/access/verify"

print("\n" + "-"*60)
print("Тест 1: Валидный токен (ожидаем ALLOW)")
print("-"*60)

response = client.post(url, {
    "gate_id": "smoke-gate-01",
    "token": token.key
}, format="json")

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

print("\n" + "-"*60)
print("Тест 2: Невалидный токен (ожидаем DENY/TOKEN_INVALID)")
print("-"*60)

response = client.post(url, {
    "gate_id": "smoke-gate-01",
    "token": "invalid_token_12345"
}, format="json")

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

print("\n" + "="*60)
print("✓ Smoke test завершён успешно!")
print("="*60 + "\n")

