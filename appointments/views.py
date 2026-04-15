from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Appointment
from .serializers import AppointmentSerializer
from users.permissions import IsAdminUserRole
from datetime import date

TIME_SLOTS = ["10:00 AM", "11:30 AM", "01:00 PM", "02:30 PM", "04:00 PM", "05:30 PM"]

class AppointmentView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [AllowAny()]  # Allow guest bookings too

    def get(self, request):
        # Returns available slots for a given date
        selected_date = request.query_params.get('date', None)
        if not selected_date:
            return Response({'message': 'date query param required'}, status=status.HTTP_400_BAD_REQUEST)

        booked_slots = Appointment.objects.filter(
            date=selected_date,
            status__in=['pending', 'confirmed']
        ).values_list('time_slot', flat=True)

        available_slots = [slot for slot in TIME_SLOTS if slot not in booked_slots]

        return Response({
            'message': 'Available slots',
            'date': selected_date,
            'available_slots': available_slots,
            'booked_slots': list(booked_slots),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user if request.user.is_authenticated else None
            serializer.save(user=user)
            return Response(
                {'message': 'Appointment booked successfully', 'data': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'message': 'Booking failed', 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class AppointmentDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        return [IsAdminUserRole()]

    def patch(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            new_status  = request.data.get('status')
            if new_status not in dict(Appointment.STATUS_CHOICES):
                return Response({'message': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
            appointment.status = new_status
            appointment.save()
            return Response(
                {'message': 'Status updated', 'data': AppointmentSerializer(appointment).data},
                status=status.HTTP_200_OK
            )
        except Appointment.DoesNotExist:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.delete()
            return Response({'message': 'Appointment deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Appointment.DoesNotExist:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminAppointmentListView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        appointments  = Appointment.objects.all().order_by('-created_at')
        if status_filter:
            appointments = appointments.filter(status=status_filter)
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(
            {'message': 'All appointments', 'data': serializer.data, 'total': appointments.count()},
            status=status.HTTP_200_OK
        )


class UserAppointmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        appointments = Appointment.objects.filter(user=request.user).order_by('-created_at')
        serializer   = AppointmentSerializer(appointments, many=True)
        return Response(
            {'message': 'Your appointments', 'data': serializer.data},
            status=status.HTTP_200_OK
        )