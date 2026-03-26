from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.serializers import ModelSerializer

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
