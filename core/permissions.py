from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q

class IsModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superuser or request.user.role in ['moderator', 'administrator'])

class IsAdministrator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superuser or request.user.role == 'administrator')

def require_trader(user):
    if not (user.is_active and user.is_verified and user.is_phone_verified and user.is_identity_verified):
        raise PermissionDenied('Email, phone and identity verification are required to trade.')

def require_unblocked(a, b):
    from accounts.models import Block
    if Block.objects.filter(Q(user=a, blocked_user=b) | Q(user=b, blocked_user=a)).exists():
        raise PermissionDenied('This interaction is unavailable.')
