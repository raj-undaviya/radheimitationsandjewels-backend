from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    TYPE_CHOICES = [
        ('virtual', 'Virtual Call'),
        ('in_store', 'In Store'),
    ]

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    customer_name    = models.CharField(max_length=255)
    phone_number     = models.CharField(max_length=20)
    email            = models.EmailField()
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='virtual')
    date             = models.DateField()
    time_slot        = models.CharField(max_length=20)  # e.g. "10:00 AM"
    description      = models.TextField(blank=True, null=True)
    reference_photo  = models.FileField(upload_to='appointments/', blank=True, null=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer_name} - {self.date} {self.time_slot}"