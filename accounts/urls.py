from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from verification.views import IdentityView
from . import views
from .oauth import GoogleLoginView, GoogleCallbackView, GoogleExchangeView

router = DefaultRouter()
router.register('blocks', views.BlockViewSet, basename='block')
urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('verify-email/<uuid:token>/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('auth/google/login/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/google/callback/', GoogleCallbackView.as_view(), name='google-callback'),
    path('auth/google/exchange/', GoogleExchangeView.as_view(), name='google-exchange'),
    path('verify-nin/', IdentityView.as_view(), name='verify-nin'),
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    path('profile/', views.UpdateProfileView.as_view(), name='update-profile'),
    path('password-reset/', views.ForgotPasswordView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.ResetPasswordView.as_view(), name='password-reset-confirm'),
    path('password-change/', views.ChangePasswordView.as_view(), name='password-change'),
    path('deactivate/', views.DeactivateAccountView.as_view(), name='deactivate-account'),
    path('notification-preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('sellers/<uuid:public_id>/', views.PublicSellerView.as_view(), name='public-seller'),
    path('users/<uuid:public_id>/', views.PublicSellerView.as_view(), name='public-user'),
    path('user-types/', views.UserTypesView.as_view(), name='user-types'),
    path('', include(router.urls)),
]
