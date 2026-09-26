from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from listings.views import CategoryViewSet, ListingViewSet
from wishlist.views import WantedItemViewSet
from matching.views import MatchView
from exchanges.views import ProposalViewSet, ExchangeViewSet
from messaging.views import MessageViewSet
from reviews.views import ReviewViewSet
from reports.views import ReportViewSet, DisputeViewSet
from notifications.views import NotificationViewSet
from locations.views import LocationViewSet
from verification.views import IdentityView, PhoneSendView, PhoneVerifyView, PossessionView
from moderation.views import (AdminUserViewSet, ModerationListingViewSet, IdentityReviewViewSet,
    PossessionReviewViewSet, ReportReviewViewSet, DisputeReviewViewSet, AuditViewSet)
from core.views import health, DashboardView

router = DefaultRouter()
for prefix, view, name in [
    ('categories', CategoryViewSet, 'category'), ('listings', ListingViewSet, 'listing'),
    ('wishlist', WantedItemViewSet, 'wanted-item'), ('proposals', ProposalViewSet, 'proposal'),
    ('exchanges', ExchangeViewSet, 'exchange'), ('messages', MessageViewSet, 'message'),
    ('reviews', ReviewViewSet, 'review'), ('reports', ReportViewSet, 'report'),
    ('disputes', DisputeViewSet, 'dispute'), ('notifications', NotificationViewSet, 'notification'),
    ('locations', LocationViewSet, 'location'), ('admin/users', AdminUserViewSet, 'admin-user'),
    ('admin/listings', ModerationListingViewSet, 'admin-listing'),
    ('admin/identity', IdentityReviewViewSet, 'admin-identity'),
    ('admin/possession', PossessionReviewViewSet, 'admin-possession'),
    ('admin/reports', ReportReviewViewSet, 'admin-report'), ('admin/disputes', DisputeReviewViewSet, 'admin-dispute'),
    ('admin/audit', AuditViewSet, 'admin-audit')]:
    router.register(prefix, view, basename=name)

urlpatterns = [
    path('admin/', admin.site.urls), path('health/', health),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/accounts/', include('accounts.urls')),
    path('api/matches/', MatchView.as_view()), path('api/dashboard/', DashboardView.as_view()),
    path('api/verification/identity/', IdentityView.as_view()),
    path('api/verification/phone/send/', PhoneSendView.as_view()),
    path('api/verification/phone/verify/', PhoneVerifyView.as_view()),
    path('api/verification/possession/<uuid:listing_id>/', PossessionView.as_view()),
    path('api/', include(router.urls)),
]
