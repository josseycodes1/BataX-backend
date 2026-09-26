from rest_framework import serializers
from accounts.serializers import PublicUserSerializer
from .models import Category, ItemListing, ItemMedia


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'is_prohibited']


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemMedia
        fields = ['id', 'url', 'caption']


class ListingSerializer(serializers.ModelSerializer):
    owner = PublicUserSerializer(read_only=True)
    images = MediaSerializer(many=True, read_only=True)

    class Meta:
        model = ItemListing
        fields = ['id', 'owner', 'title', 'category', 'brand', 'model', 'description', 'condition',
                  'age_months', 'defects', 'accessories', 'state', 'city', 'open_to_offers', 'status',
                  'possession_verified', 'images', 'created_at', 'updated_at']
        read_only_fields = ['status', 'possession_verified', 'created_at', 'updated_at']

    def validate_category(self, category):
        if category.is_prohibited:
            raise serializers.ValidationError('This category is prohibited.')
        return category


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    caption = serializers.CharField(required=False, max_length=200, allow_blank=True)
