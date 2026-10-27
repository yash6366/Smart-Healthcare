from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Public representation of a User. Never leaks password hashes or tokens.
    """
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone_number",
            "is_verified",
            "created_at",
        ]
        read_only_fields = ["id", "role", "is_verified", "created_at"]


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for public patient registration.
    Enforces that public signups can only ever create PATIENT accounts.
    """
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized

    def validate_username(self, value):
        cleaned = value.strip()
        if User.objects.filter(username__iexact=cleaned).exists():
            raise serializers.ValidationError("An account with this username already exists.")
        return cleaned

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # Validate password strength
        validate_password(password)
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        username = validated_data.pop("username")

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password,
                role=User.Role.PATIENT,
                is_verified=True,
                **validated_data,
            )
            # Create associated PatientProfile
            from apps.patients.models import PatientProfile
            PatientProfile.objects.create(user=user)

        return user


class LoginSerializer(serializers.Serializer):
    """
    Validates user credentials and generates JWT token pair.
    """
    email_or_username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})

    def validate(self, attrs):
        login_id = attrs.get("email_or_username", "").strip()
        password = attrs.get("password")

        user = None
        # Try lookup by email first, then username
        if "@" in login_id:
            try:
                user_obj = User.objects.get(email__iexact=login_id)
                if user_obj.check_password(password):
                    user = user_obj
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(username=login_id, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials. Please verify your username/email and password.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Please contact support.")

        refresh = RefreshToken.for_user(user)
        # Include role in token claims
        refresh["role"] = user.role
        refresh["email"] = user.email

        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer to safely update an authenticated user's password.
    """
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password does not match.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "New passwords do not match."})

        validate_password(attrs["new_password"], user=self.context["request"].user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """
    Serializer to blacklist a SimpleJWT refresh token upon logout.
    """
    refresh = serializers.CharField(required=True)

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError({"refresh": "Invalid or expired token."})
