import secrets
from urllib.parse import urlencode
import requests
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import UserSerializer
from .views import AuthView
from core.serializers import EmptySerializer, GoogleExchangeSerializer


def consume(key):
    value = cache.get(key)
    if value is None or not cache.add(key + ':consumed', True, timeout=600):
        raise ValidationError('Invalid or expired authorization code.')
    cache.delete(key)
    return value


class GoogleLoginView(AuthView):
    serializer_class = EmptySerializer
    def get(self, request):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise APIException('Google authentication is not configured.')
        state = secrets.token_urlsafe(32)
        cache.set('google:state:' + state, True, timeout=600)
        request.session['google_state'] = state
        return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': settings.GOOGLE_CLIENT_ID, 'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'response_type': 'code', 'scope': 'openid email profile', 'state': state}))


class GoogleCallbackView(AuthView):
    serializer_class = EmptySerializer
    def get(self, request):
        state = request.query_params.get('state', '')
        if not state or not secrets.compare_digest(state, request.session.pop('google_state', '')):
            raise ValidationError('Invalid OAuth state.')
        consume('google:state:' + state)
        try:
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'code': request.query_params.get('code', ''), 'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET, 'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'}, timeout=15)
            response.raise_for_status()
            info = requests.get('https://openidconnect.googleapis.com/v1/userinfo',
                headers={'Authorization': 'Bearer ' + response.json()['access_token']}, timeout=15)
            info.raise_for_status()
            profile = info.json()
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise APIException('Google authentication failed.') from exc
        if not profile.get('email_verified') or not profile.get('email'):
            raise ValidationError('A verified Google email is required.')
        code = secrets.token_urlsafe(32)
        cache.set('google:exchange:' + code, {'email': profile['email'].lower(),
            'first_name': profile.get('given_name', ''), 'last_name': profile.get('family_name', '')}, timeout=120)
        return redirect(settings.FRONTEND_URL + '/auth/google/callback?' + urlencode({'code': code}))


class GoogleExchangeView(AuthView):
    serializer_class = GoogleExchangeSerializer
    def post(self, request):
        from django.utils import timezone
        from rest_framework import serializers
        code = serializers.CharField(max_length=200).run_validation(request.data.get('code'))
        profile = cache.get('google:exchange:' + code)
        if not profile:
            raise ValidationError('Invalid or expired authorization code.')
        user = User.objects.filter(email__iexact=profile['email']).first()
        if not user and request.data.get('accept_terms') is not True:
            raise ValidationError({'accept_terms': 'You must accept the terms.'})
        consume('google:exchange:' + code)
        if user and not user.is_active:
            raise ValidationError('Account is inactive.')
        if user is None:
            user = User.objects.create_user(**profile, is_verified=True, terms_accepted_at=timezone.now())
        elif not user.is_verified:
            user.is_verified = True
            user.save(update_fields=['is_verified'])
        token = RefreshToken.for_user(user)
        return Response({'access': str(token.access_token), 'refresh': str(token), 'user': UserSerializer(user).data})
