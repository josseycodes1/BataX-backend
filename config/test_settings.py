import os
os.environ.setdefault('SECRET_KEY', 'test-only-secret-key-not-for-deployment-123456')
from .settings import *
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
SECURE_SSL_REDIRECT = False
CELERY_TASK_ALWAYS_EAGER = True
MIDDLEWARE = [item for item in MIDDLEWARE if item != 'whitenoise.middleware.WhiteNoiseMiddleware']
