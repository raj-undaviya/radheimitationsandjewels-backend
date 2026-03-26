from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):

    USER_ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )

    phonenumber = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, default='customer')
    token = models.CharField(max_length=255, blank=True, null=True)
    profile_image = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username
    
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        # OTP expires after 10 minutes
        return (timezone.now() - self.created_at).seconds > 600