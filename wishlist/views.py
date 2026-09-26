from rest_framework import serializers, viewsets
from .models import WantedItem


class WantedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WantedItem
        fields = ['id', 'listing', 'title', 'category', 'brand', 'model', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, data):
        listing = data.get('listing', getattr(self.instance, 'listing', None))
        if listing and listing.owner_id != self.context['request'].user.pk:
            raise serializers.ValidationError('The listing must belong to you.')
        title = data.get('title', getattr(self.instance, 'title', ''))
        category = data.get('category', getattr(self.instance, 'category', None))
        if not title and not category:
            raise serializers.ValidationError('Specify an item title or category.')
        if category and category.is_prohibited:
            raise serializers.ValidationError('This category is prohibited.')
        return data


class WantedItemViewSet(viewsets.ModelViewSet):
    serializer_class = WantedItemSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return WantedItem.objects.none()
        return WantedItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
