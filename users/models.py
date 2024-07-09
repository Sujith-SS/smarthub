from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

# Otp for signup

class OTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at



# forgotpassword For store otp expiry
# class PasswordResetOTP(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     otp = models.CharField(max_length=6)
#     expires_at = models.DateTimeField()

#     def is_expired(self):
#         return timezone.now() > self.expires_at
