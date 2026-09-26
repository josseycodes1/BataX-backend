from django.conf import settings
from django.db import models
from core.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=50)
    text = models.CharField(max_length=255)
    object_id = models.UUIDField(null=True)
    read_at = models.DateTimeField(null=True)
