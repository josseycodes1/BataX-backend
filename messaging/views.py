from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.media import upload_image, private_image_url
from exchanges.services import participants, eligible, notify
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(write_only=True, required=False)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'proposal', 'sender', 'body', 'image', 'image_url', 'read_at', 'created_at']
        read_only_fields = ['sender', 'read_at', 'created_at']

    def get_image_url(self, obj) -> str | None:
        return private_image_url(obj.image_public_id) if obj.image_public_id else None

    def validate(self, data):
        participants(data['proposal'], self.context['request'].user)
        eligible(data['proposal'])
        if data['proposal'].status not in ['pending', 'accepted', 'countered']:
            raise serializers.ValidationError('This conversation is closed.')
        if not data.get('body') and not data.get('image'):
            raise serializers.ValidationError('A message or image is required.')
        return data


class MessageViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageSerializer
    filterset_fields = ['proposal']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()
        return Message.objects.filter(Q(proposal__sender=self.request.user) | Q(proposal__recipient=self.request.user))

    def perform_create(self, serializer):
        image = serializer.validated_data.pop('image', None)
        public_id = upload_image(image, 'messages', private=True)['public_id'] if image else ''
        message = serializer.save(sender=self.request.user, image_public_id=public_id)
        proposal = message.proposal
        recipient = proposal.recipient if proposal.sender_id == self.request.user.pk else proposal.sender
        notify(recipient, 'message', proposal, 'You received an exchange message.')

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        message = self.get_object()
        if message.sender_id != request.user.pk and message.read_at is None:
            message.read_at = timezone.now()
            message.save(update_fields=['read_at'])
        return Response(self.get_serializer(message).data)
