from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, mixins, viewsets
from exchanges.models import Exchange
from exchanges.services import participants, lock_items
from core.media import upload_image, private_image_url
from .models import Report, Dispute


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'target_type', 'target_id', 'reason', 'description', 'status', 'resolution', 'created_at']
        read_only_fields = ['status', 'resolution', 'created_at']

    def validate(self, data):
        from accounts.models import User
        from listings.models import ItemListing
        from messaging.models import Message
        from reviews.models import Review
        models = {'user': User, 'listing': ItemListing, 'message': Message, 'exchange': Exchange, 'review': Review}
        target = models[data['target_type']].objects.filter(pk=data['target_id']).first()
        if not target:
            raise serializers.ValidationError('Target not found.')
        if data['target_type'] in ['message', 'exchange']:
            participants(target.proposal, self.context['request'].user)
        if data['target_type'] == 'listing' and target.status != 'active' and target.owner_id != self.context['request'].user.pk:
            raise serializers.ValidationError('Target not found.')
        return data


class ReportViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Report.objects.none()
        return Report.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class DisputeSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(write_only=True, required=False)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Dispute
        fields = ['id', 'exchange', 'complainant', 'reason', 'description', 'image', 'image_url', 'status', 'resolution', 'created_at']
        read_only_fields = ['complainant', 'status', 'resolution', 'created_at']

    def get_image_url(self, obj) -> str | None:
        return private_image_url(obj.image_public_id) if obj.image_public_id else None

    def validate_exchange(self, exchange):
        participants(exchange.proposal, self.context['request'].user)
        return exchange


class DisputeViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = DisputeSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Dispute.objects.none()
        return Dispute.objects.filter(Q(exchange__proposal__sender=self.request.user) | Q(exchange__proposal__recipient=self.request.user))

    @transaction.atomic
    def perform_create(self, serializer):
        initial = serializer.validated_data['exchange']
        lock_items(initial.proposal.offered_item_id, initial.proposal.requested_item_id)
        exchange = Exchange.objects.select_for_update().get(pk=initial.pk)
        if exchange.status not in ['agreed', 'completed'] or Dispute.objects.filter(exchange=exchange).exists():
            raise serializers.ValidationError('This exchange cannot open another dispute.')
        image = serializer.validated_data.pop('image', None)
        public_id = upload_image(image, 'disputes', private=True)['public_id'] if image else ''
        serializer.save(complainant=self.request.user, image_public_id=public_id)
        exchange.status = 'disputed'
        exchange.save(update_fields=['status'])
        from audit.models import record
        record(self.request.user, 'exchange.disputed', exchange)
