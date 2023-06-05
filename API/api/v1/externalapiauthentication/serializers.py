from rest_framework import serializers


class ExternalAuthenticationSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    apikey = serializers.CharField(required=True)
