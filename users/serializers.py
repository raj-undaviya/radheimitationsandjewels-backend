from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ModelSerializer
from rest_framework.parsers import MultiPartParser, FormParser
import cloudinary.uploader

from .models import User

class AuthenticateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"

class AuthenticateSerializerWithToken(AuthenticateSerializer):
    token = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phonenumber', 'is_staff', 'token']

    def get_token(self, obj):
        token = RefreshToken.for_user(obj)
        return str(token.access_token)

class AdminProfileSerializer(serializers.ModelSerializer):

    profile_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'username',
            'email',
            'phonenumber',
            'profile_image',
            'profile_image_url',
            'role',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'role', 'created_at', 'updated_at', 'profile_image_url']

    def get_profile_image_url(self, obj):
        return obj.profile_image if obj.profile_image else None

    def validate_email(self, value):
        # ✅ Ensure email is unique — exclude current user
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


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password     = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
