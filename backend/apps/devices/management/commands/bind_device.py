import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.devices.models import Device

User = get_user_model()

class Command(BaseCommand):
    help = "Bind a static token device to a user. Generates a token if not provided."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--token", required=False)
        parser.add_argument("--android-id", required=False)

    def handle(self, *args, **opts):
        username = opts["username"]
        token = opts.get("token") or secrets.token_hex(32)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found") from None

        device = Device.objects.create(
            user=user,
            auth_token=token,
            is_active=True,
            android_device_id=opts.get("android_id")
        )
        self.stdout.write(self.style.SUCCESS("Device bound:"))
        self.stdout.write(f"  username = {username}")
        self.stdout.write(f"  device_id = {device.id}")
        self.stdout.write(f"  token = {token}")
