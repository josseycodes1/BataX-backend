from django.conf import settings
from django.db import models
from core.models import BaseModel


class AuditEvent(BaseModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    object_id = models.UUIDField(null=True)
    details = models.JSONField(default=dict)


def record(actor, action, obj, **details):
    AuditEvent.objects.create(actor=actor, action=action, object_id=obj.pk, details=details)
