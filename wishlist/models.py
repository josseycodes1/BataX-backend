from django.conf import settings
from django.db import models
from core.models import BaseModel


class WantedItem(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wants')
    listing = models.ForeignKey('listings.ItemListing', on_delete=models.CASCADE, related_name='wants', null=True, blank=True)
    title = models.CharField(max_length=160, blank=True)
    category = models.ForeignKey('listings.Category', on_delete=models.PROTECT, null=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
