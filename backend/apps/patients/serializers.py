from rest_framework import serializers
from .models import PatientProfile
from apps.accounts.serializers import UserSerializer


class PatientProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for Patient Profile management.
    Includes user details and handles safe updates.
    """
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "user",
            "date_of_birth",
            "gender",
            "blood_group",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "address",
            "city",
            "state",
            "postal_code",
            "created_at",
            "updated_at",
            "first_name",
            "last_name",
            "phone_number",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        # Extract user fields if provided
        first_name = validated_data.pop("first_name", None)
        last_name = validated_data.pop("last_name", None)
        phone_number = validated_data.pop("phone_number", None)

        user = instance.user
        user_updated = False
        if first_name is not None:
            user.first_name = first_name
            user_updated = True
        if last_name is not None:
            user.last_name = last_name
            user_updated = True
        if phone_number is not None:
            user.phone_number = phone_number
            user_updated = True
        if user_updated:
            user.save()

        return super().update(instance, validated_data)
