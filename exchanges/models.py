from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models import BaseModel


def proposal_expiry():
    return timezone.now() + timedelta(days=7)


class ExchangeProposal(BaseModel):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sent_proposals')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_proposals')
    offered_item = models.ForeignKey('listings.ItemListing', on_delete=models.PROTECT, related_name='offers_sent')
    requested_item = models.ForeignKey('listings.ItemListing', on_delete=models.PROTECT, related_name='offers_received')
    message = models.TextField(blank=True, max_length=2000)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[(s, s.title()) for s in
        ['pending', 'accepted', 'declined', 'countered', 'cancelled', 'expired']])
    expires_at = models.DateTimeField(default=proposal_expiry)


class Exchange(BaseModel):
    proposal = models.OneToOneField(ExchangeProposal, on_delete=models.PROTECT, related_name='exchange')
    status = models.CharField(max_length=20, default='agreed', choices=[(s, s.title()) for s in
        ['agreed', 'completed', 'disputed', 'cancelled']])
    sender_confirmed_at = models.DateTimeField(null=True, blank=True)
    recipient_confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    meeting_details = models.TextField(blank=True, max_length=2000)
