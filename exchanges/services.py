from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError
from core.permissions import require_trader, require_unblocked
from listings.models import ItemListing
from notifications.models import Notification
from audit.models import record


def participants(proposal, user):
    if user.pk not in [proposal.sender_id, proposal.recipient_id]:
        raise PermissionDenied('Only exchange participants can access this resource.')


def eligible(proposal):
    require_trader(proposal.sender)
    require_trader(proposal.recipient)
    require_unblocked(proposal.sender, proposal.recipient)


def lock_items(*ids):
    return list(ItemListing.objects.select_for_update().filter(pk__in=ids).order_by('pk'))


def notify(user, kind, obj, text):
    Notification.objects.create(user=user, kind=kind, object_id=obj.pk, text=text)


def validate_items(sender, offered, requested):
    require_trader(sender)
    require_trader(requested.owner)
    require_unblocked(sender, requested.owner)
    if offered.owner_id != sender.pk or requested.owner_id == sender.pk:
        raise ValidationError('Offer your own item for another user’s item.')
    if any(item.status != 'active' or item.category.is_prohibited for item in [offered, requested]):
        raise ValidationError('Both items must be active and permitted.')
