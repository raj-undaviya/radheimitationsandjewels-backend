from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsAdminUserRole
import cloudinary.uploader
from .models import User, PasswordResetOTP, Address
from .serializers import AuthenticateSerializer, AuthenticateSerializerWithToken, AdminProfileSerializer, ChangePasswordSerializer, AddressSerializer, UserProfileSerializer
import random
from datetime import datetime
from django.core.mail import send_mail


class AuthenticateView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        data = request.data

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
            
            # -------- LOGIN --------
            email = data.get("email")
            password = data.get("password")

            user = User.objects.filter(email=email).first()
            print("Found user for email:", email, "User:", user)

            if user and user.check_password(password):

                serializer = AuthenticateSerializerWithToken(user)

                user.token = serializer.data["token"]
                user.is_active = True
                user.last_login = datetime.now()
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
    
class LogoutView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        user.token = None
        user.is_active = False
        user.save()
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    
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
        
class AdminProfileView(APIView):
    """
    GET  — fetch logged-in admin's profile
    PUT  — update profile fields
    """
    permission_classes = [IsAuthenticated, IsAdminUserRole]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        serializer = AdminProfileSerializer(request.user)
        return Response(
            {
                "message": "Admin profile retrieved successfully",
                "data":    serializer.data
            },
            status=status.HTTP_200_OK
        )

    def put(self, request):
        data          = request.data.copy()
        profile_image = request.FILES.get('profile_image')

        # ✅ Upload new profile image to Cloudinary if provided
        if profile_image:
            try:
                upload_result     = cloudinary.uploader.upload(
                    profile_image,
                    folder          = "admin_profiles/",
                    transformation = [{"width": 400, "height": 400, "crop": "fill", "gravity": "face"}]
                )
                data['profile_image'] = upload_result['secure_url']
            except Exception as e:
                return Response(
                    {"message": f"Image upload failed: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = AdminProfileSerializer(request.user, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Profile updated successfully",
                    "data":    serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "message": "Profile update failed",
                "errors":  serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class AdminChangePasswordView(APIView):
    """
    POST — change password for logged-in admin
    """
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"message": "Validation failed", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user             = request.user
        current_password = serializer.validated_data['current_password']
        new_password     = serializer.validated_data['new_password']

        # ✅ Verify current password
        if not user.check_password(current_password):
            return Response(
                {"message": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Prevent reusing same password
        if user.check_password(new_password):
            return Response(
                {"message": "New password must be different from current password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password changed successfully. Please login again."},
            status=status.HTTP_200_OK
        )


class AdminProfileImageDeleteView(APIView):
    """
    DELETE — remove profile image and reset to null
    """
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def delete(self, request):
        user              = request.user
        user.profile_image = None
        user.save()

        return Response(
            {"message": "Profile image removed successfully"},
            status=status.HTTP_200_OK
        )

# ── User Profile ──────────────────────────────────────────────

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user       = request.user
        addresses  = Address.objects.filter(user=user).order_by('-is_default', '-created_at')
        default_address = addresses.filter(is_default=True).first()

        return Response({
            'message': 'Profile retrieved successfully',
            'data': {
                'id':            user.id,
                'first_name':    user.first_name,
                'last_name':     user.last_name,
                'username':      user.username,
                'email':         user.email,
                'phonenumber':   user.phonenumber,
                'profile_image': str(user.profile_image) if user.profile_image else None,
                'role':          user.role,
                'is_active':     user.is_active,
                'created_at':    user.created_at.isoformat(),
                'addresses':     AddressSerializer(addresses, many=True).data,
                'default_address': AddressSerializer(default_address).data if default_address else None,
            }
        }, status=status.HTTP_200_OK)

    def put(self, request):
        user          = request.user
        data          = request.data.copy()
        profile_image = request.FILES.get('profile_image')

        # ✅ Upload to Cloudinary if new image provided
        if profile_image:
            try:
                upload_result = cloudinary.uploader.upload(
                    profile_image,
                    folder         = 'user_profiles/',
                    transformation = [{"width": 400, "height": 400, "crop": "fill", "gravity": "face"}]
                )
                user.profile_image = upload_result['secure_url']
            except Exception as e:
                return Response(
                    {'message': f'Image upload failed: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Update allowed fields only
        user.first_name  = data.get('first_name',  user.first_name)
        user.last_name   = data.get('last_name',   user.last_name)
        user.username    = data.get('username',    user.username)
        user.phonenumber = data.get('phonenumber', user.phonenumber)

        # ✅ Check username uniqueness
        if User.objects.exclude(id=user.id).filter(username=user.username).exists():
            return Response(
                {'message': 'Username already taken'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Check phone uniqueness
        if User.objects.exclude(id=user.id).filter(phonenumber=user.phonenumber).exists():
            return Response(
                {'message': 'Phone number already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.save()

        return Response({
            'message': 'Profile updated successfully',
            'data': {
                'id':            user.id,
                'first_name':    user.first_name,
                'last_name':     user.last_name,
                'username':      user.username,
                'email':         user.email,
                'phonenumber':   user.phonenumber,
                'profile_image': str(user.profile_image) if user.profile_image else None,
            }
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        """Remove profile image."""
        user               = request.user
        user.profile_image = None
        user.save()
        return Response(
            {'message': 'Profile image removed'},
            status=status.HTTP_200_OK
        )


# ── Addresses ─────────────────────────────────────────────────

class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all addresses — default first."""
        addresses  = Address.objects.filter(user=request.user)
        serializer = AddressSerializer(addresses, many=True)
        return Response({
            'message': 'Addresses retrieved',
            'data':    serializer.data,
            'total':   addresses.count(),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """Add new address."""
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            # ✅ If this is user's first address, auto set as default
            if not Address.objects.filter(user=request.user).exists():
                serializer.save(user=request.user, is_default=True)
            else:
                serializer.save(user=request.user)

            return Response({
                'message': 'Address added successfully',
                'data':    serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'message': 'Validation failed',
            'errors':  serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Address.objects.get(pk=pk, user=user)
        except Address.DoesNotExist:
            return None

    def get(self, request, pk):
        address = self.get_object(pk, request.user)
        if not address:
            return Response({'message': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'message': 'Address retrieved',
            'data':    AddressSerializer(address).data
        })

    def patch(self, request, pk):
        """Update address fields partially."""
        address = self.get_object(pk, request.user)
        if not address:
            return Response({'message': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Address updated',
                'data':    serializer.data
            })
        return Response({
            'message': 'Validation failed',
            'errors':  serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete address. If it was default, auto-assign next address as default."""
        address = self.get_object(pk, request.user)
        if not address:
            return Response({'message': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)

        was_default = address.is_default
        address.delete()

        # ✅ Auto assign next address as default if deleted one was default
        if was_default:
            next_address = Address.objects.filter(user=request.user).first()
            if next_address:
                next_address.is_default = True
                next_address.save()

        return Response({'message': 'Address deleted'}, status=status.HTTP_204_NO_CONTENT)


class SetDefaultAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        """Set address as default — removes default from all others automatically."""
        try:
            address            = Address.objects.get(pk=pk, user=request.user)
            address.is_default = True
            address.save()     # model's save() handles removing old default
            return Response({
                'message': 'Default address updated',
                'data':    AddressSerializer(address).data
            })
        except Address.DoesNotExist:
            return Response({'message': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)