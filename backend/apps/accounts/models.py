from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class PasswordHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_history")
    password = models.CharField(max_length=255)  # stores password hash
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
