from rest_framework import serializers, mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from exchanges.services import participants
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'exchange', 'author', 'recipient', 'rating', 'comment', 'created_at']
        read_only_fields = ['author', 'recipient', 'created_at']

    def validate_exchange(self, exchange):
        user = self.context['request'].user
        participants(exchange.proposal, user)
        if exchange.status != 'completed':
            raise serializers.ValidationError('Only completed exchanges can be reviewed.')
        if Review.objects.filter(exchange=exchange, author=user).exists():
            raise serializers.ValidationError('You have already reviewed this exchange.')
        return exchange


class ReviewViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    filterset_fields = ['recipient']

    def get_permissions(self):
        return [IsAuthenticated()] if self.action == 'create' else [AllowAny()]

    def perform_create(self, serializer):
        proposal = serializer.validated_data['exchange'].proposal
        recipient = proposal.recipient if proposal.sender_id == self.request.user.pk else proposal.sender
        serializer.save(author=self.request.user, recipient=recipient)
