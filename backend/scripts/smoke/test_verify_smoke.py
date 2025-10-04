#!/usr/bin/env python3
"""Smoke-тест для /api/v1/access/verify через Django shell"""
import os
import sys

import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accessproj.settings.test')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

# Применяем миграции для тестовой БД
from django.core.management import call_command

call_command('migrate', '--run-syncdb', verbosity=0)

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.access.models import AccessPermission, AccessPoint

User = get_user_model()

def run_tests():
    print("=" * 60)
    print("SMOKE TEST: /api/v1/access/verify с DRF user-token + RBAC")
    print("=" * 60)

    client = APIClient()
    url = "/api/v1/access/verify"

    # Cleanup
    User.objects.all().delete()
    AccessPoint.objects.all().delete()

    # Test 1: ALLOW с валидным user token + RBAC разрешение
    print("\n[TEST 1] ALLOW: валидный user token + RBAC")
    print("-" * 60)
    user = User.objects.create_user(username="testuser", password="pass123", is_active=True)
    token = Token.objects.create(user=user)
    gate = AccessPoint.objects.create(code="gate-01", name="Test Gate")

    # RBAC: даём разрешение пользователю (Вариант 1)
    AccessPermission.objects.create(access_point=gate, user=user, allow=True)

    response = client.post(url, {
        "gate_id": "gate-01",
        "token": token.key
    }, format="json")

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ALLOW"
    assert data["reason"] == "OK"
    assert data["duration_ms"] == 800
    print("✅ PASSED")

    # Test 2: DENY с невалидным token
    print("\n[TEST 2] DENY: невалидный token")
    print("-" * 60)
    response = client.post(url, {
        "gate_id": "gate-01",
        "token": "invalid"
    }, format="json")

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DENY"
    assert data["reason"] == "TOKEN_INVALID"
    print("✅ PASSED")

    # Test 3: DENY с несуществующим gate
    print("\n[TEST 3] DENY: несуществующий gate")
    print("-" * 60)
    response = client.post(url, {
        "gate_id": "gate-99",
        "token": token.key
    }, format="json")

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DENY"
    assert data["reason"] == "UNKNOWN_GATE"
    print("✅ PASSED")

    # Test 4: DENY с пустым запросом
    print("\n[TEST 4] DENY: пустой запрос")
    print("-" * 60)
    response = client.post(url, {}, format="json")

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DENY"
    assert data["reason"] == "INVALID_REQUEST"
    print("✅ PASSED")

    # Test 5: DENY с отсутствием RBAC разрешения (NO_PERMISSION)
    print("\n[TEST 5] DENY: нет RBAC разрешения (NO_PERMISSION)")
    print("-" * 60)
    user2 = User.objects.create_user(username="user_no_perm", password="pass", is_active=True)
    token2 = Token.objects.create(user=user2)
    AccessPoint.objects.create(code="gate-restricted", name="Restricted Gate")
    # НЕ создаём AccessPermission

    response = client.post(url, {
        "gate_id": "gate-restricted",
        "token": token2.key
    }, format="json")

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DENY"
    assert data["reason"] == "NO_PERMISSION"
    print("✅ PASSED")

    print("\n" + "=" * 60)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ: 5/5 ✅")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

