import secrets
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone
from .models import EmailChallenge

def send_verification(user):
    code = f'{secrets.randbelow(1000000):06d}'
    challenge, _ = EmailChallenge.objects.update_or_create(user=user, defaults={
        'code_hash': make_password(code), 'token': uuid.uuid4(), 'attempts': 0,
        'expires_at': timezone.now() + timedelta(minutes=10)})
    link = f'{settings.API_BASE_URL}/api/accounts/verify-email/{challenge.token}/'
    send_mail('Verify your BataX email', f'Your code is {code}. It expires in 10 minutes.\n{link}',
              settings.DEFAULT_FROM_EMAIL, [user.email])
