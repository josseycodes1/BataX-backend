from django.conf import settings
from django.db import models
from core.models import BaseModel


class Message(BaseModel):
    proposal = models.ForeignKey('exchanges.ExchangeProposal', on_delete=models.PROTECT, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=5000, blank=True)
    image_public_id = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
