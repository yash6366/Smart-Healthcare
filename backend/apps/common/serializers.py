from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField(required=False, allow_null=True)


class APIErrorResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="error")
    error = ErrorDetailSerializer()

