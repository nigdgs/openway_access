from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from rest_framework.authtoken.models import Token
from apps.access.models import AccessPoint, AccessPermission, AccessEvent
from apps.devices.models import Device
import secrets

class Command(BaseCommand):
    help = "Purge demo data and create clean admin+demo, gate, permissions, and a fresh device token."

    def add_arguments(self, parser):
        parser.add_argument("--admin-user", default="admin")
        parser.add_argument("--admin-pass", default="StrongPass_123")
        parser.add_argument("--admin-email", default="admin@example.com")
        parser.add_argument("--demo-user", default="demo")
        parser.add_argument("--demo-pass", default="StrongPass_123")
        parser.add_argument("--gate-code", default="gate-01")
        parser.add_argument("--gate-name", default="Gate 01")
        parser.add_argument("--group-name", default="USER")
        parser.add_argument("--keep-gates", action="store_true", help="Do not delete existing access points")

    @transaction.atomic
    def handle(self, *args, **opts):
        User = get_user_model()
        admin_user = opts["admin_user"]
        admin_pass = opts["admin_pass"]
        admin_email = opts["admin_email"]
        demo_user = opts["demo_user"]
        demo_pass = opts["demo_pass"]
        gate_code = opts["gate_code"]
        gate_name = opts["gate_name"]
        group_name = opts["group_name"]
        keep_gates = opts["keep_gates"]

        self.stdout.write(self.style.WARNING("Purging access events..."))
        AccessEvent.objects.all().delete()

        self.stdout.write(self.style.WARNING("Deleting devices..."))
        Device.objects.all().delete()

        self.stdout.write(self.style.WARNING("Deleting permissions..."))
        AccessPermission.objects.all().delete()

        if not keep_gates:
            self.stdout.write(self.style.WARNING("Deleting access points..."))
            AccessPoint.objects.all().delete()

        self.stdout.write(self.style.WARNING("Deleting DRF auth tokens..."))
        Token.objects.all().delete()

        self.stdout.write(self.style.WARNING("Deleting users..."))
        User.objects.all().delete()

        # Recreate admin
        admin = User.objects.create_user(username=admin_user, email=admin_email)
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(admin_pass)
        admin.save()
        Token.objects.get_or_create(user=admin)

        # Recreate demo
        demo = User.objects.create_user(username=demo_user, email=f"{demo_user}@example.com")
        demo.is_active = True
        demo.set_password(demo_pass)
        demo.save()
        Token.objects.get_or_create(user=demo)

        # Create group and assign
        group, _ = Group.objects.get_or_create(name=group_name)
        demo.groups.add(group)

        # Create gate
        ap, _ = AccessPoint.objects.get_or_create(code=gate_code, defaults={"name": gate_name})

        # Permission: group has allow at gate
        AccessPermission.objects.create(access_point=ap, group=group, allow=True)

        # Create device token for demo
        token = secrets.token_hex(32)
        device = Device.objects.create(user=demo, auth_token=token, is_active=True)

        self.stdout.write(self.style.SUCCESS("Reset completed"))
        self.stdout.write(f" Admin: {admin_user} / {admin_pass}")
        self.stdout.write(f" Demo : {demo_user} / {demo_pass}")
        self.stdout.write(f" Gate : {ap.code} ({ap.name})")
        self.stdout.write(f" Group: {group.name} (demo in group)")
        self.stdout.write(f" Device id: {device.id}")
        self.stdout.write(self.style.SUCCESS(f" Device token: {token}"))


