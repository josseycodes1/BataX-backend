from django.conf import settings
from django.db import models
from core.models import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    is_prohibited = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ItemListing(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_REVIEW = 'pending_review', 'Pending review'
        ACTIVE = 'active', 'Active'
        IN_EXCHANGE = 'in_exchange', 'In exchange'
        EXCHANGED = 'exchanged', 'Exchanged'
        PAUSED = 'paused', 'Paused'
        REJECTED = 'rejected', 'Rejected'
        REMOVED = 'removed', 'Removed'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='listings')
    title = models.CharField(max_length=160)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=5000)
    condition = models.CharField(max_length=20, choices=[(x, x.title()) for x in ['new', 'like_new', 'good', 'fair']])
    age_months = models.PositiveIntegerField(null=True, blank=True)
    defects = models.TextField(blank=True, max_length=2000)
    accessories = models.TextField(blank=True, max_length=2000)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    open_to_offers = models.BooleanField(default=False)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFT, db_index=True)
    possession_verified = models.BooleanField(default=False)


class ItemMedia(BaseModel):
    listing = models.ForeignKey(ItemListing, on_delete=models.CASCADE, related_name='images')
    url = models.URLField(max_length=500)
    public_id = models.CharField(max_length=255)
    caption = models.CharField(max_length=200, blank=True)
