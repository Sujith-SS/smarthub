from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .utils import generate_otp, send_otp_email
from .models import UserProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.userprofile.save()


@receiver(post_save, sender=User)
def send_otp_on_user_creation(sender, instance, created, **kwargs):
    if created and not instance.is_active:
        otp = generate_otp()
        expires_at = timezone.now() + timedelta(minutes=5)
        instance.userprofile.otp = otp
        instance.userprofile.otp_expires_at = expires_at
        instance.userprofile.save()
        send_otp_email(instance.email, otp)


@receiver(post_save, sender=User)
def activate_user(sender, instance, **kwargs):
    if instance.is_active and not kwargs.get('created'):
        # This signal can be used to perform additional actions upon user activation
        pass
