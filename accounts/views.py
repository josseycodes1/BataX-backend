from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .models import User, UserProfile, EmailChallenge, ContactMessage, Block
from .serializers import (RegisterSerializer, UserSerializer, PublicUserSerializer, ProfileSerializer,
    PreferenceSerializer, CredentialsSerializer, EmailSerializer, OTPSerializer,
    PasswordChangeSerializer, PasswordResetSerializer)
from .services import send_verification
from core.serializers import DetailSerializer, LogoutSerializer, DeactivateSerializer, UserTypeSerializer


def validated(cls, request):
    serializer = cls(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class AuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class RegisterView(AuthView):
    serializer_class = RegisterSerializer

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification(user)
        return Response({'detail': 'Registration successful. Please check your email to verify your account.'}, status=201)


class LoginView(AuthView):
    serializer_class = CredentialsSerializer

    def post(self, request):
        data = validated(CredentialsSerializer, request)
        user = authenticate(request, email=data['email'].strip().lower(), password=data['password'])
        if not user:
            raise ValidationError({'detail': 'Invalid email or password.'})
        if not user.is_verified:
            raise ValidationError({'detail': 'Please verify your email before logging in.'})
        token = RefreshToken.for_user(user)
        return Response({'access': str(token.access_token), 'refresh': str(token), 'user': UserSerializer(user).data})


class VerifyOTPView(AuthView):
    serializer_class = OTPSerializer

    def post(self, request):
        data = validated(OTPSerializer, request)
        valid = False
        with transaction.atomic():
            challenge = EmailChallenge.objects.select_for_update().filter(user__email__iexact=data['email']).first()
            if challenge and challenge.expires_at > timezone.now() and challenge.attempts < 5:
                challenge.attempts += 1
                challenge.save(update_fields=['attempts'])
                if check_password(data['otp'], challenge.code_hash):
                    User.objects.filter(pk=challenge.user_id, is_active=True).update(is_verified=True)
                    challenge.delete()
                    valid = True
        if not valid:
            raise ValidationError('Invalid or expired verification code.')
        return Response({'detail': 'Email verified.'})


class VerifyEmailView(AuthView):
    serializer_class = DetailSerializer
    @transaction.atomic
    def get(self, request, token):
        challenge = get_object_or_404(EmailChallenge.objects.select_for_update(), token=token,
                                     expires_at__gt=timezone.now(), user__is_active=True)
        User.objects.filter(pk=challenge.user_id).update(is_verified=True)
        challenge.delete()
        return Response({'detail': 'Email verified.'})


class ResendOTPView(AuthView):
    serializer_class = EmailSerializer

    def post(self, request):
        data = validated(EmailSerializer, request)
        user = User.objects.filter(email__iexact=data['email'], is_verified=False, is_active=True).first()
        if user:
            send_verification(user)
        return Response({'detail': 'If eligible, a verification email has been sent.'})


class LogoutView(APIView):
    serializer_class = LogoutSerializer
    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh', ''))
            if str(token['user_id']) != str(request.user.pk):
                raise TokenError('Wrong user')
            token.blacklist()
        except TokenError:
            raise ValidationError('Invalid refresh token.')
        return Response({'detail': 'Logged out.'})


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UpdateProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class PublicSellerView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicUserSerializer
    queryset = User.objects.filter(is_active=True).select_related('profile')
    lookup_field = 'public_id'


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = PreferenceSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return UserProfile.objects.get_or_create(user=self.request.user)[0]


def set_password(user, password):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ValidationError({'new_password': exc.messages})
    user.set_password(password)
    user.save(update_fields=['password'])
    for token in user.outstandingtoken_set.all():
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        BlacklistedToken.objects.get_or_create(token=token)


class ForgotPasswordView(AuthView):
    serializer_class = EmailSerializer

    def post(self, request):
        data = validated(EmailSerializer, request)
        user = User.objects.filter(email__iexact=data['email'], is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_mail('Reset your BataX password', f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}',
                      settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({'detail': 'If the account exists, a reset link has been sent.'})


class ResetPasswordView(AuthView):
    serializer_class = PasswordResetSerializer

    @transaction.atomic
    def post(self, request):
        data = validated(PasswordResetSerializer, request)
        try:
            user = User.objects.select_for_update().get(pk=urlsafe_base64_decode(data['uid']).decode(), is_active=True)
        except (ValueError, UnicodeDecodeError, DjangoValidationError, User.DoesNotExist):
            raise ValidationError('Invalid reset link.')
        if not default_token_generator.check_token(user, data['token']):
            raise ValidationError('Invalid or expired reset link.')
        set_password(user, data['new_password'])
        return Response({'detail': 'Password reset.'})


class ChangePasswordView(APIView):
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        data = validated(PasswordChangeSerializer, request)
        if not request.user.check_password(data['old_password']):
            raise ValidationError({'old_password': 'Incorrect password.'})
        set_password(request.user, data['new_password'])
        return Response({'detail': 'Password changed. Sign in again.'})


class DeactivateAccountView(APIView):
    serializer_class = DeactivateSerializer
    @transaction.atomic
    def post(self, request):
        from exchanges.models import Exchange
        from django.db.models import Q
        if not request.user.check_password(request.data.get('password', '')):
            raise ValidationError({'password': 'Confirm your password.'})
        if Exchange.objects.filter(Q(proposal__sender=request.user) | Q(proposal__recipient=request.user),
                                   status__in=['agreed', 'disputed']).exists():
            raise ValidationError('Resolve active exchanges before deactivating your account.')
        request.user.is_active = False
        request.user.save(update_fields=['is_active'])
        request.user.listings.exclude(status='exchanged').update(status='removed')
        return Response({'detail': 'Account deactivated.'})


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']


class ContactView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ContactSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class UserTypesView(APIView):
    serializer_class = UserTypeSerializer
    permission_classes = [AllowAny]

    def get(self, request):
        return Response([{'value': value, 'label': label, 'self_registration': value == 'user'} for value, label in User.Role.choices])


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ['id', 'blocked_user', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_blocked_user(self, user):
        if user == self.context['request'].user:
            raise ValidationError('You cannot block yourself.')
        return user


class BlockViewSet(viewsets.ModelViewSet):
    serializer_class = BlockSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Block.objects.none()
        return Block.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.get_queryset().filter(blocked_user=serializer.validated_data['blocked_user']).exists():
            raise ValidationError('User already blocked.')
        serializer.save(user=self.request.user)
