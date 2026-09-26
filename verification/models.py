from django.conf import settings
from django.db import models
from core.models import BaseModel


class IdentityVerification(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='identity_checks')
    provider = models.CharField(max_length=100)
    reference = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default='pending', choices=[(s, s.title()) for s in ['pending', 'approved', 'rejected']])
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True)


class PhoneChallenge(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)


class PossessionVerification(BaseModel):
    listing = models.OneToOneField('listings.ItemListing', on_delete=models.CASCADE, related_name='possession')
    code = models.CharField(max_length=20)
    expires_at = models.DateTimeField()
    image_public_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[(s, s.title()) for s in ['pending', 'submitted', 'approved', 'rejected']])
