import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from core.models import BaseModel

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        UserProfile.objects.get_or_create(user=user)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True, role='super_admin', is_verified=True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        MODERATOR = 'moderator', 'Moderator'
        ADMIN = 'administrator', 'Administrator'
        SUPER_ADMIN = 'super_admin', 'Super Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    phone_number = models.CharField(max_length=20, blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_identity_verified = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='unique_email_case_insensitive')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=1000)
    profile_image = models.URLField(blank=True, max_length=500)
    image_public_id = models.CharField(max_length=255, blank=True)
    new_messages_email = models.BooleanField(default=True)
    new_messages_in_app = models.BooleanField(default=True)
    exchange_updates_email = models.BooleanField(default=True)
    weekly_digest_email = models.BooleanField(default=False)

class EmailChallenge(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)

class ContactMessage(BaseModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField(max_length=5000)

class Block(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'blocked_user'], name='unique_user_block')]
