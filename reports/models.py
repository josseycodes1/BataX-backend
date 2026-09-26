from django.conf import settings
from django.db import models
from core.models import BaseModel


class Report(BaseModel):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    target_type = models.CharField(max_length=20, choices=[(s, s.title()) for s in ['user', 'listing', 'message', 'exchange', 'review']])
    target_id = models.UUIDField()
    reason = models.CharField(max_length=100)
    description = models.TextField(max_length=5000)
    status = models.CharField(max_length=20, default='open', choices=[(s, s.title()) for s in ['open', 'under_review', 'resolved', 'closed']])
    resolution = models.TextField(blank=True)


class Dispute(BaseModel):
    exchange = models.OneToOneField('exchanges.Exchange', on_delete=models.PROTECT, related_name='dispute')
    complainant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.CharField(max_length=100)
    description = models.TextField(max_length=5000)
    image_public_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='open', choices=[(s, s.title()) for s in ['open', 'under_review', 'resolved', 'closed']])
    resolution = models.TextField(blank=True)
