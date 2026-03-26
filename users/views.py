from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import User, PasswordResetOTP
from .serializers import AuthenticateSerializer, AuthenticateSerializerWithToken
import random
from django.core.mail import send_mail


class AuthenticateView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        data = request.data
        print("Received authentication request with data:", data)

        # -------- REGISTER --------
        if all(k in data for k in ["phonenumber", "first_name", "last_name", "username", "password"]):
            print("Registering user with data:", data)

            serializer = AuthenticateSerializer(data=data)

            if serializer.is_valid():
                user = serializer.save()

                user.set_password(data["password"])
                user.save()

                print("User created successfully:", user)

                return Response(
                    {"message": "User created successfully", "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"message": "User creation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            print("Login attempt with data:", data)
            # -------- LOGIN --------
            email = data.get("email")
            password = data.get("password")

            user = User.objects.filter(email=email).first()
            print("Found user for email:", email, "User:", user)

            if user and user.check_password(password):

                serializer = AuthenticateSerializerWithToken(user)

                user.token = serializer.data["token"]
                user.save()

                return Response(
                    {"message": "Login successful", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"message": "Invalid email or password", "errors": {"email": ["Invalid email or password"]}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'message': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists or not (security best practice)
            return Response(
                {'message': 'If this email exists, an OTP has been sent'},
                status=status.HTTP_200_OK
            )

        # Generate 6 digit OTP
        otp = str(random.randint(100000, 999999))

        # Invalidate any previous unused OTPs for this user
        PasswordResetOTP.objects.filter(user=user, is_used=False).delete()

        # Save new OTP
        PasswordResetOTP.objects.create(user=user, otp=otp)

        # Send OTP email
        send_mail(
            subject='Password Reset OTP',
            message=f'Your OTP for password reset is: {otp}\nIt is valid for 10 minutes.',
            from_email='your_email@gmail.com',
            recipient_list=[email],
            fail_silently=False
        )

        return Response(
            {'message': 'If this email exists, an OTP has been sent'},
            status=status.HTTP_200_OK
        )

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not all([email, otp, new_password]):
            return Response(
                {'message': 'Email, OTP and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'message': 'Invalid email'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            otp_record = PasswordResetOTP.objects.get(
                user=user,
                otp=otp,
                is_used=False
            )
        except PasswordResetOTP.DoesNotExist:
            return Response(
                {'message': 'Invalid or already used OTP'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check expiry
        if otp_record.is_expired():
            otp_record.delete()
            return Response(
                {'message': 'OTP has expired, please request a new one'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset password
        user.set_password(new_password)
        user.save()

        # Mark OTP as used
        otp_record.is_used = True
        otp_record.save()

        return Response(
            {'message': 'Password reset successfully'},
            status=status.HTTP_200_OK
        )
    
class CustomersView(APIView):

    permission_classes = [IsAdminUser]
    def get(self, request):
        customers = User.objects.filter(role='customer', is_staff=False)
        data = [
            {
                "id": customer.id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "username": customer.username,
                "email": customer.email,
                "phone": customer.phonenumber,
                "profile_image": customer.profile_image,
                "is_active": customer.is_active,
                "created_at": customer.created_at.isoformat(),
                "updated_at": customer.updated_at.isoformat(),
            } for customer in customers]
        return Response({'message': 'Customers retrieved successfully', 'customers': data}, status=status.HTTP_200_OK)
    
class CustomersDetailView(APIView):

    permission_classes = [IsAdminUser]
    def get(self, request, customer_id):
        try:
            customer = User.objects.get(id=customer_id, role='customer', is_staff=False)
            data = {
                "id": customer.id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "username": customer.username,
                "email": customer.email,
                "phone": customer.phonenumber,
                "profile_image": customer.profile_image,
                "is_active": customer.is_active,
                "created_at": customer.created_at.isoformat(),
                "updated_at": customer.updated_at.isoformat(),
            }
            return Response({'message': 'Customer retrieved successfully', 'customer': data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, customer_id):
        try:
            customer = User.objects.get(id=customer_id, role='customer')
            data = request.data

            customer.first_name = data.get('first_name', customer.first_name)
            customer.last_name = data.get('last_name', customer.last_name)
            customer.username = data.get('username', customer.username)
            customer.phonenumber = data.get('phone', customer.phonenumber)
            customer.profile_image = data.get('profile_image', customer.profile_image)
            customer.save()

            return Response({'message': 'Customer updated successfully', 'data': data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)


    def delete(self, request, customer_id):
        try:
            customer = User.objects.get(id=customer_id, role='customer')
            customer.delete()
            return Response({'message': 'Customer deleted successfully'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)