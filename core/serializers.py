from rest_framework import serializers


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class EmptySerializer(serializers.Serializer):
    pass


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class DeactivateSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class UserTypeSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    self_registration = serializers.BooleanField()


class GoogleExchangeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=200)
    accept_terms = serializers.BooleanField(required=False)


class PhoneOTPSerializer(serializers.Serializer):
    otp = serializers.RegexField(r'^\d{6}$')


class DashboardSerializer(serializers.Serializer):
    active_listings = serializers.IntegerField()
    pending_offers = serializers.IntegerField()
    active_exchanges = serializers.IntegerField()
    completed_exchanges = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
