# policies/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Policy(models.Model):

    TYPE_CHOICES = [
        ('terms_and_conditions', 'Terms & Conditions'),
        ('shipping_policy',      'Shipping Policy'),
        ('refund_and_return',    'Refund & Return'),
        ('privacy_policy',       'Privacy Policy'),
        ('cookie_policy',        'Cookie Policy'),
        ('disclaimer',           'Disclaimer'),
    ]

    title       = models.CharField(max_length=255)
    policy_type = models.CharField(max_length=50, choices=TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)   # short summary shown on card
    content     = models.TextField()                         # full policy content
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def is_outdated(self):
        # ✅ Policy is outdated if not updated in 6 months
        return self.updated_at < timezone.now() - timedelta(days=180)


class PolicyAudit(models.Model):
    """Tracks when the next audit is scheduled"""
    next_audit_date  = models.DateField()
    compliance_score = models.PositiveIntegerField(default=100)  # 0-100
    notes            = models.TextField(blank=True, null=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Audit - {self.next_audit_date}"