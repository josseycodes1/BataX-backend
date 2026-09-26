from django.db import models
from core.models import BaseModel


class Location(BaseModel):
    country = models.CharField(max_length=2, default='NG')
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['country', 'state', 'city'], name='unique_location')]
