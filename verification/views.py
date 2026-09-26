import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, generics
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from core.media import upload_image
from listings.models import ItemListing
from .models import IdentityVerification, PhoneChallenge, PossessionVerification
from core.serializers import EmptySerializer, PhoneOTPSerializer
from listings.serializers import ImageUploadSerializer


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityVerification
        fields = ['id', 'provider', 'reference', 'status', 'created_at', 'reviewed_at']
        read_only_fields = ['status', 'created_at', 'reviewed_at']


class IdentityView(generics.ListCreateAPIView):
    serializer_class = IdentitySerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return IdentityVerification.objects.none()
        return IdentityVerification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_verified or not self.request.user.is_phone_verified:
            raise ValidationError('Verify email and phone first.')
        if self.get_queryset().filter(status='pending').exists():
            raise ValidationError('You already have a pending identity review.')
        # A supplied reference is only a review request, never proof of identity.
        serializer.save(user=self.request.user)


class PhoneSendView(APIView):
    serializer_class = EmptySerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        import requests
        phone = request.user.phone_number
        serializers.RegexField(r'^\+[1-9]\d{7,14}$').run_validation(phone)
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_FROM_NUMBER:
            raise APIException('SMS delivery is not configured.')
        code = f'{secrets.randbelow(1000000):06d}'
        with transaction.atomic():
            PhoneChallenge.objects.update_or_create(user=request.user, defaults={'phone_number': phone,
                'code_hash': make_password(code), 'attempts': 0, 'expires_at': timezone.now() + timedelta(minutes=10)})
            try:
                result = requests.post(f'https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json',
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN), timeout=15,
                    data={'To': phone, 'From': settings.TWILIO_FROM_NUMBER, 'Body': f'Your BataX verification code is {code}.'})
                result.raise_for_status()
            except requests.RequestException as exc:
                raise APIException('SMS delivery is unavailable. Please retry.') from exc
        return Response({'detail': 'Verification code sent.'})


class PhoneVerifyView(APIView):
    serializer_class = PhoneOTPSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        code = serializers.RegexField(r'^\d{6}$').run_validation(request.data.get('otp'))
        valid = False
        with transaction.atomic():
            challenge = PhoneChallenge.objects.select_for_update().filter(user=request.user).first()
            if challenge and challenge.attempts < 5 and challenge.expires_at > timezone.now() and challenge.phone_number == request.user.phone_number:
                challenge.attempts += 1
                challenge.save(update_fields=['attempts'])
                if check_password(code, challenge.code_hash):
                    request.user.is_phone_verified = True
                    request.user.save(update_fields=['is_phone_verified'])
                    challenge.delete()
                    valid = True
        if not valid:
            raise ValidationError('Invalid or expired verification code.')
        return Response({'detail': 'Phone verified.'})


class PossessionView(APIView):
    serializer_class = ImageUploadSerializer
    @transaction.atomic
    def post(self, request, listing_id):
        listing = get_object_or_404(ItemListing.objects.select_for_update(), pk=listing_id, owner=request.user)
        if listing.status not in ['draft', 'paused', 'rejected']:
            raise ValidationError('Only draft, paused or rejected listings can start a possession check.')
        check, _ = PossessionVerification.objects.update_or_create(listing=listing, defaults={
            'code': 'BX-' + secrets.token_hex(4).upper(), 'expires_at': timezone.now() + timedelta(minutes=15),
            'status': 'pending', 'image_public_id': ''})
        listing.possession_verified = False
        listing.save(update_fields=['possession_verified'])
        return Response({'id': check.pk, 'code': check.code, 'expires_at': check.expires_at,
                         'instruction': 'Upload a photo of the item beside a handwritten copy of this code.'}, status=201)

    @transaction.atomic
    def patch(self, request, listing_id):
        listing = get_object_or_404(ItemListing.objects.select_for_update(), pk=listing_id, owner=request.user)
        check = get_object_or_404(PossessionVerification.objects.select_for_update(), listing=listing)
        if check.expires_at <= timezone.now() or check.status != 'pending':
            raise ValidationError('This challenge is expired or already submitted.')
        result = upload_image(request.data.get('image'), 'possession', private=True)
        check.image_public_id = result['public_id']
        check.status = 'submitted'
        check.save()
        return Response({'id': check.pk, 'status': check.status})
