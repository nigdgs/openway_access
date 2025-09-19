from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.contrib.auth.hashers import check_password

class RecentPasswordValidator:
    def __init__(self, history_size=5):
        self.history_size = history_size

    def validate(self, password, user=None):
        if not user or not user.pk:
            return
        recent = user.password_history.all()[: self.history_size]
        for entry in recent:
            if check_password(password, entry.password):
                raise ValidationError(
                    _("You cannot reuse a recent password."),
                    code="password_no_recent_reuse",
                )

    def get_help_text(self):
        return _("Your new password must not match the last N previously used passwords.")