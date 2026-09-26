import os
from datetime import timedelta
from pathlib import Path

import cloudinary
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.environ['SECRET_KEY']
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'rest_framework_simplejwt.token_blacklist', 'corsheaders',
    'django_filters', 'drf_spectacular', 'accounts', 'verification', 'listings',
    'wishlist', 'matching', 'exchanges', 'messaging', 'reviews', 'reports',
    'moderation', 'notifications', 'locations', 'audit', 'core',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
              'OPTIONS': {'context_processors': ['django.template.context_processors.request',
                         'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.getenv('DB_NAME', 'batax'),
    'USER': os.getenv('DB_USER', 'batax'), 'PASSWORD': os.getenv('DB_PASSWORD', ''),
    'HOST': os.getenv('DB_HOST', 'localhost'), 'PORT': os.getenv('DB_PORT', '5432'), 'CONN_MAX_AGE': 60}}
AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.' + name} for name in
    ['UserAttributeSimilarityValidator', 'MinimumLengthValidator', 'CommonPasswordValidator', 'NumericPasswordValidator']]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination', 'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend', 'rest_framework.filters.SearchFilter'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '100/hour', 'user': '1000/hour', 'auth': '10/minute'},
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15), 'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
              'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': True, 'CHECK_REVOKE_TOKEN': True}
SPECTACULAR_SETTINGS = {'TITLE': 'BataX API', 'VERSION': '1.0.0', 'COMPONENT_SPLIT_REQUEST': True}
SPECTACULAR_SETTINGS['ENUM_NAME_OVERRIDES'] = {
    'ListingStatus': [('draft', 'Draft'), ('pending_review', 'Pending review'), ('active', 'Active'),
        ('in_exchange', 'In exchange'), ('exchanged', 'Exchanged'), ('paused', 'Paused'),
        ('rejected', 'Rejected'), ('removed', 'Removed')],
    'ProposalStatus': [(s, s.title()) for s in ['pending', 'accepted', 'declined', 'countered', 'cancelled', 'expired']],
    'ExchangeStatus': [(s, s.title()) for s in ['agreed', 'completed', 'disputed', 'cancelled']],
    'ReviewStatus': [(s, s.title()) for s in ['open', 'under_review', 'resolved', 'closed']],
    'IdentityStatus': [(s, s.title()) for s in ['pending', 'approved', 'rejected']],
    'PossessionStatus': [(s, s.title()) for s in ['pending', 'submitted', 'approved', 'rejected']],
}
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000').split(',')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}}
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULE = {'expire-proposals': {'task': 'exchanges.tasks.expire_proposals', 'schedule': 300},
                        'clear-tokens': {'task': 'core.tasks.clear_tokens', 'schedule': 86400}}
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'BataX <noreply@example.com>')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
cloudinary.config(cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'), api_key=os.getenv('CLOUDINARY_API_KEY'),
                  api_secret=os.getenv('CLOUDINARY_API_SECRET'), secure=True)
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_SSL_REDIRECT = not DEBUG
SECURE_REDIRECT_EXEMPT = [r'^health/$']
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER', '')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', API_BASE_URL + '/api/accounts/auth/google/callback/')
PASSWORD_RESET_TIMEOUT = 3600
# Enable only behind a proxy which strips incoming X-Forwarded-Proto headers.
if os.getenv('TRUST_PROXY', 'false').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
