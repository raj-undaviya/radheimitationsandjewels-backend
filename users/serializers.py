# users/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ModelSerializer
from .models import Address, User


# ── Auth ──────────────────────────────────────────────────────

class AuthenticateSerializer(ModelSerializer):
    class Meta:
        model  = User
        fields = "__all__"


class AuthenticateSerializerWithToken(ModelSerializer):
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name',
            'phonenumber', 'role',
            'profile_image', 'is_staff', 'token'
        ]

    def get_token(self, obj):
        token = RefreshToken.for_user(obj)
        return str(token.access_token)


# ── Address ───────────────────────────────────────────────────

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Address
        fields = [
            'id', 'label', 'full_name', 'phone',
            'address_line', 'city', 'state',
            'pincode', 'country', 'is_default',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ── User Profile ──────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    addresses       = serializers.SerializerMethodField()
    default_address = serializers.SerializerMethodField()
    profile_image   = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'first_name', 'last_name',
            'username', 'email', 'phonenumber',
            'profile_image', 'role',
            'is_active', 'created_at', 'updated_at',
            'addresses', 'default_address',
        ]
        read_only_fields = ['id', 'role', 'created_at', 'updated_at']

    def get_profile_image(self, obj):
        # ✅ Always returns a clean URL string, never a Cloudinary object
        if obj.profile_image:
            return str(obj.profile_image.url) if hasattr(obj.profile_image, 'url') else str(obj.profile_image)
        return None

    def get_addresses(self, obj):
        addresses = obj.addresses.all().order_by('-is_default', '-created_at')
        return AddressSerializer(addresses, many=True).data

    def get_default_address(self, obj):
        address = obj.addresses.filter(is_default=True).first()
        return AddressSerializer(address).data if address else None


# ── Admin Profile ─────────────────────────────────────────────

class AdminProfileSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'first_name', 'last_name',
            'username', 'email', 'phonenumber',
            'profile_image', 'profile_image_url',
            'role', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'role', 'created_at', 'updated_at', 'profile_image_url']

    def get_profile_image_url(self, obj):
        if obj.profile_image:
            return str(obj.profile_image.url) if hasattr(obj.profile_image, 'url') else str(obj.profile_image)
        return None

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(id=user.id).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_username(self, value):
        user = self.instance
        if User.objects.exclude(id=user.id).filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_phonenumber(self, value):
        user = self.instance
        if User.objects.exclude(id=user.id).filter(phonenumber=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value


# ── Change Password ───────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password     = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


# ── Customer (Admin view) ─────────────────────────────────────

class CustomerSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    addresses     = AddressSerializer(many=True, read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'first_name', 'last_name',
            'username', 'email', 'phonenumber',
            'profile_image', 'is_active',
            'created_at', 'updated_at',
            'addresses',
        ]

    def get_profile_image(self, obj):
        if obj.profile_image:
            return str(obj.profile_image.url) if hasattr(obj.profile_image, 'url') else str(obj.profile_image)
        return None