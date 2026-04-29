# policies/serializers.py
from rest_framework import serializers
from .models import Policy, PolicyAudit
from django.utils import timezone


class PolicySerializer(serializers.ModelSerializer):

    print("Serializing policy:")  # Debugging line

    last_updated = serializers.SerializerMethodField(read_only=True)
    is_outdated  = serializers.ReadOnlyField()

    class Meta:
        model  = Policy
        fields = [
            'id',
            'title',
            'policy_type',
            'description',
            'content',
            'is_active',
            'is_outdated',
            'last_updated',    # human readable e.g. "Updated 12 days ago"
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_last_updated(self, obj):
        delta = timezone.now() - obj.updated_at
        days  = delta.days

        if days == 0:
            return "Updated today"
        elif days == 1:
            return "Updated yesterday"
        elif days < 30:
            return f"Updated {days} days ago"
        elif days < 365:
            months = days // 30
            return f"Updated {months} month{'s' if months > 1 else ''} ago"
        else:
            return obj.updated_at.strftime("Last updated: %b %d, %Y")


class PolicyAuditSerializer(serializers.ModelSerializer):

    compliance_score = serializers.SerializerMethodField()

    class Meta:
        model  = PolicyAudit
        fields = ['id', 'next_audit_date', 'compliance_score', 'notes', 'updated_at']

    def get_compliance_score(self, obj):
        return obj.compliance_score