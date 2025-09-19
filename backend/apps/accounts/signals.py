from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import PasswordHistory

User = get_user_model()

@receiver(pre_save, sender=User)
def mark_password_change(sender, instance, **kwargs):
    if not instance.pk:
        instance._password_changed = True
        return
    try:
        old = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        instance._password_changed = True
        return
    instance._password_changed = (old.password != instance.password)

@receiver(post_save, sender=User)
def store_password_history(sender, instance, created, **kwargs):
    if created or getattr(instance, "_password_changed", False):
        PasswordHistory.objects.create(user=instance, password=instance.password)
