from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from backend.utils.email_utils import send_appointment_email
from backend.utils.email_templates import appointment_booked_template, appointment_confirmed_template, appointment_cancelled_template, appointment_completed_template
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
            appt = serializer.save(user=user)

            # Send booking confirmation email
            try:
                send_appointment_email(
                    to_email=appt.email,
                    subject="Your appointment is booked — Radhe Imitations & Jewels",
                    html_content=appointment_booked_template(
                        name=appt.customer_name,
                        date=appt.date.strftime("%d/%m/%Y"),
                        time_slot=appt.time_slot,
                        appointment_type=appt.appointment_type,
                    )
                )
            except Exception as e:
                print(f"Email failed: {e}")  # don't break the API if email fails

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

            # Send email based on new status
            try:
                if new_status == 'confirmed':
                    html = appointment_confirmed_template(
                        name=appointment.customer_name,
                        date=appointment.date.strftime("%d/%m/%Y"),
                        time_slot=appointment.time_slot,
                        appointment_type=appointment.appointment_type,
                    )
                    subject = "Your appointment is confirmed — Radhe Imitations & Jewels"

                elif new_status == 'cancelled':
                    html = appointment_cancelled_template(
                        name=appointment.customer_name,
                        date=appointment.date.strftime("%d/%m/%Y"),
                        time_slot=appointment.time_slot,
                    )
                    subject = "Your appointment has been cancelled — Radhe Imitations & Jewels"

                elif new_status == 'completed':
                    html = appointment_completed_template(
                        name=appointment.customer_name,
                        date=appointment.date.strftime("%d/%m/%Y"),
                    )
                    subject = "Thank you for visiting us — Radhe Imitations & Jewels"

                else:
                    html = None

                if html:
                    send_appointment_email(appointment.email, subject, html)

            except Exception as e:
                print(f"Email failed: {e}")

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
    
class AdminAppointmentListView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        date_filter   = request.query_params.get('date', None)
        appointments  = Appointment.objects.all().order_by('-created_at')

        if status_filter:
            appointments = appointments.filter(status=status_filter)
        if date_filter:
            appointments = appointments.filter(date=date_filter)

        serializer = AppointmentSerializer(appointments, many=True)
        return Response({
            'message': 'All appointments',
            'data':    serializer.data,
            'total':   appointments.count(),
            'pending':   Appointment.objects.filter(status='pending').count(),
            'confirmed': Appointment.objects.filter(status='confirmed').count(),
            'cancelled': Appointment.objects.filter(status='cancelled').count(),
            'completed': Appointment.objects.filter(status='completed').count(),
        }, status=status.HTTP_200_OK)