from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from apps.access.models import AccessEvent


class Command(BaseCommand):
    help = "Purge AccessEvent older than N days (default 90)"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)

    def handle(self, *args, **opts):
        cutoff = now() - timedelta(days=opts["days"])
        n, _ = AccessEvent.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(f"Deleted {n} events older than {opts['days']} days")

