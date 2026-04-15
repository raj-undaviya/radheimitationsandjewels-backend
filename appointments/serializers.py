from rest_framework import serializers
from .models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Appointment
        fields = '__all__'
        read_only_fields = ['user', 'status', 'created_at', 'updated_at']

    def validate(self, data):
        # Prevent double booking same slot
        qs = Appointment.objects.filter(
            date=data.get('date'),
            time_slot=data.get('time_slot'),
            status__in=['pending', 'confirmed']
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This time slot is already booked.")
        return data