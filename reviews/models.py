from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from core.models import BaseModel


class Review(BaseModel):
    exchange = models.ForeignKey('exchanges.Exchange', on_delete=models.PROTECT, related_name='reviews')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='written_reviews')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='received_reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, max_length=2000)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['exchange', 'author'], name='one_review_per_participant')]
