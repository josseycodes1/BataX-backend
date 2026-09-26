from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import ExchangeProposal, Exchange
from .serializers import ProposalSerializer, ExchangeSerializer
from .services import lock_items, validate_items, eligible, notify
from listings.models import ItemListing
from audit.models import record


class ProposalViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ProposalSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ExchangeProposal.objects.none()
        return ExchangeProposal.objects.filter(Q(sender=self.request.user) | Q(recipient=self.request.user)).select_related('sender', 'recipient')

    @transaction.atomic
    def perform_create(self, serializer):
        offered, requested = serializer.validated_data['offered_item'], serializer.validated_data['requested_item']
        items = {item.pk: item for item in lock_items(offered.pk, requested.pk)}
        validate_items(self.request.user, items[offered.pk], items[requested.pk])
        if ExchangeProposal.objects.filter(sender=self.request.user, offered_item=offered, requested_item=requested,
                                           status='pending', expires_at__gt=timezone.now()).exists():
            raise ValidationError('A pending proposal already exists for these items.')
        proposal = serializer.save(sender=self.request.user, recipient=requested.owner)
        notify(proposal.recipient, 'proposal', proposal, 'You received an exchange proposal.')
        record(self.request.user, 'proposal.created', proposal)

    def pending(self, proposal):
        if proposal.status != 'pending' or proposal.expires_at <= timezone.now():
            raise ValidationError('This proposal is no longer pending.')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, pk=None):
        initial = self.get_object()
        items = lock_items(initial.offered_item_id, initial.requested_item_id)
        proposal = ExchangeProposal.objects.select_for_update().get(pk=initial.pk)
        if proposal.recipient_id != request.user.pk:
            raise PermissionDenied('Only the recipient can accept.')
        self.pending(proposal)
        eligible(proposal)
        if any(item.status != 'active' or item.category.is_prohibited for item in items):
            raise ValidationError('An item is no longer available.')
        proposal.status = 'accepted'
        proposal.save(update_fields=['status'])
        ids = [item.pk for item in items]
        ItemListing.objects.filter(pk__in=ids).update(status='in_exchange')
        ExchangeProposal.objects.filter(Q(offered_item_id__in=ids) | Q(requested_item_id__in=ids), status='pending').update(status='cancelled')
        exchange = Exchange.objects.create(proposal=proposal)
        notify(proposal.sender, 'accepted', exchange, 'Your exchange proposal was accepted.')
        record(request.user, 'exchange.agreed', exchange)
        return Response(ExchangeSerializer(exchange).data, status=201)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def decline(self, request, pk=None):
        proposal = ExchangeProposal.objects.select_for_update().get(pk=self.get_object().pk)
        if proposal.recipient_id != request.user.pk:
            raise PermissionDenied('Only the recipient can decline.')
        self.pending(proposal)
        proposal.status = 'declined'
        proposal.save(update_fields=['status'])
        return Response(ProposalSerializer(proposal).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        proposal = ExchangeProposal.objects.select_for_update().get(pk=self.get_object().pk)
        if proposal.sender_id != request.user.pk:
            raise PermissionDenied('Only the sender can cancel.')
        self.pending(proposal)
        proposal.status = 'cancelled'
        proposal.save(update_fields=['status'])
        return Response(ProposalSerializer(proposal).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def counter(self, request, pk=None):
        initial = self.get_object()
        serializer = ProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offered, requested = serializer.validated_data['offered_item'], serializer.validated_data['requested_item']
        items = {item.pk: item for item in lock_items(offered.pk, requested.pk)}
        original = ExchangeProposal.objects.select_for_update().get(pk=initial.pk)
        if original.recipient_id != request.user.pk or requested.owner_id != original.sender_id:
            raise PermissionDenied('Counter-offers must reverse the original participants.')
        self.pending(original)
        validate_items(request.user, items[offered.pk], items[requested.pk])
        original.status = 'countered'
        original.save(update_fields=['status'])
        counter = serializer.save(sender=request.user, recipient=original.sender, parent=original)
        notify(original.sender, 'counter', counter, 'You received a counter-offer.')
        return Response(ProposalSerializer(counter).data, status=201)


class MeetingSerializer(serializers.Serializer):
    meeting_details = serializers.CharField(max_length=2000)


class ExchangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExchangeSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Exchange.objects.none()
        return Exchange.objects.filter(Q(proposal__sender=self.request.user) | Q(proposal__recipient=self.request.user)).select_related('proposal')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def confirm(self, request, pk=None):
        initial = self.get_object()
        lock_items(initial.proposal.offered_item_id, initial.proposal.requested_item_id)
        exchange = Exchange.objects.select_for_update().get(pk=initial.pk)
        eligible(exchange.proposal)
        if exchange.status != 'agreed':
            raise ValidationError('Only agreed exchanges can be confirmed.')
        field = 'sender_confirmed_at' if request.user.pk == exchange.proposal.sender_id else 'recipient_confirmed_at'
        if not getattr(exchange, field):
            setattr(exchange, field, timezone.now())
        if exchange.sender_confirmed_at and exchange.recipient_confirmed_at:
            exchange.status = 'completed'
            exchange.completed_at = timezone.now()
            ItemListing.objects.filter(pk__in=[exchange.proposal.offered_item_id, exchange.proposal.requested_item_id]).update(status='exchanged')
            for user in [exchange.proposal.sender, exchange.proposal.recipient]:
                notify(user, 'completed', exchange, 'Both participants confirmed the exchange.')
        exchange.save()
        record(request.user, 'exchange.confirmed', exchange)
        return Response(ExchangeSerializer(exchange).data)

    @action(detail=True, methods=['patch'], serializer_class=MeetingSerializer)
    @transaction.atomic
    def meeting(self, request, pk=None):
        exchange = Exchange.objects.select_for_update().get(pk=self.get_object().pk)
        eligible(exchange.proposal)
        if exchange.status != 'agreed':
            raise ValidationError('Meeting details can only change for agreed exchanges.')
        serializer = MeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exchange.meeting_details = serializer.validated_data['meeting_details']
        exchange.save(update_fields=['meeting_details'])
        return Response(ExchangeSerializer(exchange).data)
