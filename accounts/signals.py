from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import AccountUser, PreviousPasswords


@receiver(post_save, sender=AccountUser)
def create_previous_passwords(instance: AccountUser, created: bool, **kwargs):
    if created:
        PreviousPasswords.objects.create(user=instance)
