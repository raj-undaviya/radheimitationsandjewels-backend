import cloudinary.models
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
    profile_image  = cloudinary.models.CloudinaryField('profile_images', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username
    
    @property
    def profile_image_url(self):
        """Always returns a usable URL string for the profile image."""
        if self.profile_image:
            return self.profile_image.url
        return None
    
class Address(models.Model):

    ADDRESS_TYPE_CHOICES = (
        ('home',   'Home'),
        ('office', 'Office'),
        ('other',  'Other'),
    )

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label        = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='home')
    full_name    = models.CharField(max_length=100)
    phone        = models.CharField(max_length=20)
    address_line = models.TextField()                          # street / flat / building
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=100)
    pincode      = models.CharField(max_length=10)
    country      = models.CharField(max_length=100, default='India')
    is_default   = models.BooleanField(default=False)         # ✅ default address for orders
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering         = ['-is_default', '-created_at']    # default address always first
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f"{self.user.username} — {self.label} ({self.city})"

    def save(self, *args, **kwargs):
        # ✅ If this address is set as default,
        #    remove default from all other addresses of same user
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        # OTP expires after 10 minutes
        return (timezone.now() - self.created_at).seconds > 600