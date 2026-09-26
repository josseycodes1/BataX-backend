from celery import shared_task
from django.utils import timezone
from .models import ExchangeProposal


@shared_task
def expire_proposals():
    return ExchangeProposal.objects.filter(status='pending', expires_at__lte=timezone.now()).update(status='expired')
