from rest_framework import serializers


class GlobalSearchSerializer(serializers.Serializer):
    q         = serializers.CharField(required=False, allow_blank=True)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )