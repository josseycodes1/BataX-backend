from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from core.permissions import require_trader, IsAdministrator
from core.media import upload_image
from .models import Category, ItemListing, ItemMedia
from .serializers import CategorySerializer, ListingSerializer, ImageUploadSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        return [AllowAny()] if self.action in ['list', 'retrieve'] else [IsAdministrator()]


class ListingViewSet(viewsets.ModelViewSet):
    serializer_class = ListingSerializer
    filterset_fields = ['category', 'condition', 'state', 'city', 'brand', 'possession_verified']
    search_fields = ['title', 'description', 'brand', 'model']

    def get_permissions(self):
        return [AllowAny()] if self.action in ['list', 'retrieve'] else super().get_permissions()

    def get_queryset(self):
        qs = ItemListing.objects.select_related('owner__profile', 'category').prefetch_related('images')
        public = Q(status='active', owner__is_active=True, category__is_prohibited=False)
        if self.request.user.is_authenticated:
            if self.action == 'mine':
                return qs.filter(owner=self.request.user)
            return qs.filter(public | Q(owner=self.request.user))
        return qs.filter(public)

    def perform_create(self, serializer):
        require_trader(self.request.user)
        serializer.save(owner=self.request.user)

    def owned(self, listing):
        if listing.owner_id != self.request.user.pk:
            raise PermissionDenied('Only the owner can change this listing.')
        if listing.status in ['in_exchange', 'exchanged', 'removed']:
            raise ValidationError('This listing cannot be changed in its current state.')

    @transaction.atomic
    def perform_update(self, serializer):
        listing = ItemListing.objects.select_for_update().get(pk=serializer.instance.pk)
        self.owned(listing)
        require_trader(self.request.user)
        serializer.instance = listing
        serializer.save(status='draft', possession_verified=False)
        from verification.models import PossessionVerification
        PossessionVerification.objects.filter(listing=listing).update(status='rejected')
        self.cancel_proposals(listing)

    @staticmethod
    def cancel_proposals(listing):
        from exchanges.models import ExchangeProposal
        ExchangeProposal.objects.filter(Q(offered_item=listing) | Q(requested_item=listing), status='pending').update(status='cancelled')

    @transaction.atomic
    def perform_destroy(self, instance):
        instance = ItemListing.objects.select_for_update().get(pk=instance.pk)
        self.owned(instance)
        instance.status = 'removed'
        instance.save(update_fields=['status'])
        self.cancel_proposals(instance)

    @action(detail=False, methods=['get'])
    def mine(self, request):
        return self.list(request)

    @action(detail=True, methods=['post'], serializer_class=ImageUploadSerializer)
    @transaction.atomic
    def images(self, request, pk=None):
        listing = ItemListing.objects.select_for_update().get(pk=self.get_object().pk)
        self.owned(listing)
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if listing.images.count() >= 10:
            raise ValidationError('At most ten images are allowed.')
        result = upload_image(serializer.validated_data['image'], 'listings')
        ItemMedia.objects.create(listing=listing, url=result['secure_url'], public_id=result['public_id'],
                                 caption=serializer.validated_data.get('caption', ''))
        listing.status = 'draft'
        listing.possession_verified = False
        listing.save(update_fields=['status', 'possession_verified'])
        from verification.models import PossessionVerification
        PossessionVerification.objects.filter(listing=listing).update(status='rejected')
        self.cancel_proposals(listing)
        return Response(ListingSerializer(listing).data, status=201)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit(self, request, pk=None):
        listing = ItemListing.objects.select_for_update().get(pk=self.get_object().pk)
        self.owned(listing)
        require_trader(request.user)
        if listing.category.is_prohibited or listing.images.count() < 2 or not listing.possession_verified:
            raise ValidationError('A permitted category, two images and approved possession evidence are required.')
        if not listing.open_to_offers and not listing.wants.exists():
            raise ValidationError('Add wanted items or enable open to offers.')
        listing.status = 'pending_review'
        listing.save(update_fields=['status'])
        return Response(ListingSerializer(listing).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def pause(self, request, pk=None):
        listing = ItemListing.objects.select_for_update().get(pk=self.get_object().pk)
        self.owned(listing)
        listing.status = 'paused'
        listing.save(update_fields=['status'])
        self.cancel_proposals(listing)
        return Response(ListingSerializer(listing).data)
