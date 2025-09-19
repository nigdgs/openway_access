from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.access.models import AccessPoint, AccessPermission
from apps.devices.models import Device
import secrets

User = get_user_model()

class Command(BaseCommand):
    help = "Seed demo data: gate-01, group USER, user demo, device with static token."

    def handle(self, *args, **options):
        ap, _ = AccessPoint.objects.get_or_create(code="gate-01", defaults={"name": "Gate 01"})
        grp, _ = Group.objects.get_or_create(name="USER")
        # User
        user, created = User.objects.get_or_create(username="demo", defaults={"is_active": True})
        if created:
            user.set_password("StrongPass_123")
            user.save()
        user.groups.add(grp)

        # Permission
        AccessPermission.objects.get_or_create(access_point=ap, group=grp, allow=True)

        # Device with static token
        token = secrets.token_hex(32)
        Device.objects.create(user=user, auth_token=token, is_active=True)

        self.stdout.write(self.style.SUCCESS("Seed complete:"))
        self.stdout.write(f"  gate_id = gate-01")
        self.stdout.write(f"  username = demo / password = StrongPass_123")
        self.stdout.write(f"  Static token = {token}")
