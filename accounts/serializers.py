from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from .models import User, UserProfile

class PublicUserSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(source='profile.bio', read_only=True)
    profile_image = serializers.URLField(source='profile.profile_image', read_only=True)
    class Meta:
        model = User
        fields = ['public_id', 'first_name', 'city', 'state', 'bio', 'profile_image', 'is_identity_verified', 'date_joined']

class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.URLField(source='profile.profile_image', read_only=True)
    bio = serializers.CharField(source='profile.bio', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'public_id', 'email', 'first_name', 'last_name', 'phone_number', 'state', 'city',
                  'role', 'is_verified', 'is_phone_verified', 'is_identity_verified', 'profile_image', 'bio']
        read_only_fields = fields

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    accept_terms = serializers.BooleanField(write_only=True)
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone_number', 'state', 'city', 'accept_terms']
        extra_kwargs = {'first_name': {'required': True}, 'last_name': {'required': True}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, data):
        if not data.pop('accept_terms'):
            raise serializers.ValidationError({'accept_terms': 'You must accept the terms.'})
        validate_password(data['password'], User(email=data['email'], first_name=data.get('first_name', ''), last_name=data.get('last_name', '')))
        return data

    def create(self, data):
        return User.objects.create_user(**data, terms_accepted_at=timezone.now())

class ProfileSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(required=False, max_length=1000, allow_blank=True)
    profile_image = serializers.ImageField(required=False, write_only=True)
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'state', 'city', 'bio', 'profile_image']

    def update(self, user, data):
        from core.media import upload_image
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if 'bio' in data:
            profile.bio = data.pop('bio')
        image = data.pop('profile_image', None)
        if image:
            result = upload_image(image, 'avatars')
            profile.profile_image, profile.image_public_id = result['secure_url'], result['public_id']
        if 'phone_number' in data and data['phone_number'] != user.phone_number:
            user.is_phone_verified = False
        profile.save()
        user.profile = profile
        return super().update(user, data)

class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['new_messages_email', 'new_messages_in_app', 'exchange_updates_email', 'weekly_digest_email']

class CredentialsSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class OTPSerializer(EmailSerializer):
    otp = serializers.RegexField(r'^\d{6}$')

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

class PasswordResetSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()
