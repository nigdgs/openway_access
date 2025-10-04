from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils.timezone import now

from apps.access.models import AccessEvent, AccessPoint

User = get_user_model()


@pytest.mark.django_db
class TestPurgeAccessEvents:
    def test_purge_old_events(self):
        """Test that purge deletes events older than cutoff and keeps recent ones."""
        # Create test data
        gate = AccessPoint.objects.create(code="gate-test", name="Test Gate")
        user = User.objects.create_user(username="testuser", password="pass123")

        # Create old event (100 days ago)
        old_event = AccessEvent.objects.create(
            access_point=gate,
            user=user,
            decision="ALLOW",
            reason="OK",
        )
        old_event.created_at = now() - timedelta(days=100)
        old_event.save(update_fields=["created_at"])

        # Create recent event (10 days ago)
        recent_event = AccessEvent.objects.create(
            access_point=gate,
            user=user,
            decision="ALLOW",
            reason="OK",
        )
        recent_event.created_at = now() - timedelta(days=10)
        recent_event.save(update_fields=["created_at"])

        # Verify both exist
        assert AccessEvent.objects.count() == 2

        # Run purge command (delete older than 90 days)
        out = StringIO()
        call_command("purge_access_events", "--days", "90", stdout=out)

        # Check results
        assert AccessEvent.objects.count() == 1
        assert AccessEvent.objects.filter(id=recent_event.id).exists()
        assert not AccessEvent.objects.filter(id=old_event.id).exists()
        assert "Deleted 1 events older than 90 days" in out.getvalue()

    def test_purge_all_with_days_zero(self):
        """Test that --days 0 deletes all events."""
        gate = AccessPoint.objects.create(code="gate-all", name="All Gate")

        # Create multiple events
        for i in range(5):
            AccessEvent.objects.create(
                access_point=gate,
                decision="ALLOW",
                reason="OK",
            )

        assert AccessEvent.objects.count() == 5

        # Run purge with days=0
        out = StringIO()
        call_command("purge_access_events", "--days", "0", stdout=out)

        # All events should be deleted
        assert AccessEvent.objects.count() == 0
        assert "Deleted 5 events older than 0 days" in out.getvalue()

    def test_purge_no_events(self):
        """Test purge when no events match the criteria."""
        # Create recent event
        gate = AccessPoint.objects.create(code="gate-recent", name="Recent Gate")
        AccessEvent.objects.create(
            access_point=gate,
            decision="ALLOW",
            reason="OK",
        )

        # Run purge for very old events
        out = StringIO()
        call_command("purge_access_events", "--days", "365", stdout=out)

        # No events should be deleted
        assert AccessEvent.objects.count() == 1
        assert "Deleted 0 events older than 365 days" in out.getvalue()

