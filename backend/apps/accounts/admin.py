from django.contrib import admin

from .models import PasswordHistory


@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__username", "user__email")
