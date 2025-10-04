import secrets

from django.core.management.base import BaseCommand, CommandError

from apps.devices.models import Device


class Command(BaseCommand):
    help = "Set or rotate the auth_token for a device. If --token is omitted, generates a new one."

    def add_arguments(self, parser):
        parser.add_argument("--device-id", type=int, required=True)
        parser.add_argument("--token", required=False)

    def handle(self, *args, **opts):
        device_id = opts["device_id"]
        token = opts.get("token") or secrets.token_urlsafe(32)

        try:
            device = Device.objects.get(pk=device_id)
        except Device.DoesNotExist:
            raise CommandError(f"Device id {device_id} not found") from None

        device.auth_token = token
        device.save(update_fields=["auth_token"])

        self.stdout.write(self.style.SUCCESS("Token set:"))
        self.stdout.write(f"  device_id = {device.id}")
        self.stdout.write(f"  auth_token = {device.auth_token}")

