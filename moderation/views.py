from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from core.permissions import IsModerator, IsAdministrator
from core.media import private_image_url
from accounts.models import User
from accounts.serializers import UserSerializer
from listings.models import ItemListing
from listings.serializers import ListingSerializer
from verification.models import IdentityVerification, PossessionVerification
from verification.views import IdentitySerializer
from reports.models import Report, Dispute
from reports.views import ReportSerializer, DisputeSerializer
from audit.models import AuditEvent, record
from exchanges.models import Exchange
from exchanges.services import lock_items


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(max_length=2000)


class StaffUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=User.Role.choices)


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserSerializer
    permission_classes = [IsAdministrator]
    search_fields = ['email', 'first_name', 'last_name']

    @action(detail=False, methods=['post'], url_path='create-account', serializer_class=StaffUserSerializer)
    def create_account(self, request):
        serializer = StaffUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not request.user.is_superuser and data['role'] in ['administrator', 'super_admin']:
            raise PermissionDenied('Only a super admin can create administrators.')
        if User.objects.filter(email__iexact=data['email']).exists():
            raise ValidationError('This email already exists.')
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(data['password'], User(email=data['email']))
        except DjangoValidationError as exc:
            raise ValidationError({'password': exc.messages})
        role = data['role']
        user = User.objects.create_user(**data, is_staff=role != 'user', is_superuser=role == 'super_admin')
        record(request.user, 'account.created', user, role=role)
        return Response(UserSerializer(user).data, status=201)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        user = self.get_object()
        if user == request.user or user.is_superuser or (user.role == 'administrator' and not request.user.is_superuser):
            raise PermissionDenied('You cannot suspend this account.')
        user.is_active = False
        user.save(update_fields=['is_active'])
        user.listings.filter(status='active').update(status='paused')
        record(request.user, 'account.suspended', user)
        return Response(UserSerializer(user).data)


class ModerationListingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ItemListing.objects.all().select_related('owner__profile').prefetch_related('images')
    serializer_class = ListingSerializer
    permission_classes = [IsModerator]
    filterset_fields = ['status']

    @action(detail=True, methods=['post'], serializer_class=DecisionSerializer)
    @transaction.atomic
    def review(self, request, pk=None):
        listing = ItemListing.objects.select_for_update().get(pk=self.get_object().pk)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if listing.status != 'pending_review':
            raise ValidationError('Only submitted listings can be reviewed.')
        if data['decision'] == 'approve':
            from core.permissions import require_trader
            require_trader(listing.owner)
            if listing.category.is_prohibited or not listing.possession_verified or listing.images.count() < 2:
                raise ValidationError('Listing does not satisfy publication requirements.')
        listing.status = 'active' if data['decision'] == 'approve' else 'rejected'
        listing.save(update_fields=['status'])
        record(request.user, 'listing.reviewed', listing, **data)
        return Response(ListingSerializer(listing).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def remove(self, request, pk=None):
        listing = ItemListing.objects.select_for_update().get(pk=self.get_object().pk)
        if listing.status in ['in_exchange', 'exchanged']:
            raise ValidationError('Resolve the exchange through the dispute workflow first.')
        listing.status = 'removed'
        listing.save(update_fields=['status'])
        from listings.views import ListingViewSet
        ListingViewSet.cancel_proposals(listing)
        record(request.user, 'listing.removed', listing)
        return Response(ListingSerializer(listing).data)


class IdentityReviewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IdentityVerification.objects.all()
    serializer_class = IdentitySerializer
    permission_classes = [IsModerator]

    @action(detail=True, methods=['post'], serializer_class=DecisionSerializer)
    @transaction.atomic
    def review(self, request, pk=None):
        check = IdentityVerification.objects.select_for_update().get(pk=self.get_object().pk)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if check.status != 'pending' or check.user_id == request.user.pk:
            raise ValidationError('Cannot review this identity request.')
        check.status = 'approved' if serializer.validated_data['decision'] == 'approve' else 'rejected'
        check.reviewed_by = request.user
        check.reviewed_at = timezone.now()
        check.save()
        User.objects.filter(pk=check.user_id).update(is_identity_verified=check.status == 'approved')
        record(request.user, 'identity.reviewed', check, **serializer.validated_data)
        return Response(IdentitySerializer(check).data)


class PossessionSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PossessionVerification
        fields = ['id', 'listing', 'code', 'expires_at', 'status', 'image_url']

    def get_image_url(self, obj) -> str | None:
        return private_image_url(obj.image_public_id) if obj.image_public_id else None


class PossessionReviewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PossessionVerification.objects.all()
    serializer_class = PossessionSerializer
    permission_classes = [IsModerator]

    @action(detail=True, methods=['post'], serializer_class=DecisionSerializer)
    @transaction.atomic
    def review(self, request, pk=None):
        initial = self.get_object()
        listing = ItemListing.objects.select_for_update().get(pk=initial.listing_id)
        check = PossessionVerification.objects.select_for_update().get(pk=initial.pk)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if check.status != 'submitted' or listing.owner_id == request.user.pk:
            raise ValidationError('Cannot review this possession request.')
        check.status = 'approved' if serializer.validated_data['decision'] == 'approve' else 'rejected'
        check.save(update_fields=['status'])
        listing.possession_verified = check.status == 'approved'
        listing.save(update_fields=['possession_verified'])
        record(request.user, 'possession.reviewed', check, **serializer.validated_data)
        return Response(PossessionSerializer(check).data)


class ResolutionSerializer(serializers.Serializer):
    resolution = serializers.CharField(max_length=5000)


class ReportReviewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsModerator]

    @action(detail=True, methods=['post'], serializer_class=ResolutionSerializer)
    def resolve(self, request, pk=None):
        report = self.get_object()
        serializer = ResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report.resolution = serializer.validated_data['resolution']
        report.status = 'resolved'
        report.save()
        record(request.user, 'report.resolved', report)
        return Response(ReportSerializer(report).data)


class DisputeResolutionSerializer(ResolutionSerializer):
    outcome = serializers.ChoiceField(choices=['completed', 'cancelled'])


class DisputeReviewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Dispute.objects.all()
    serializer_class = DisputeSerializer
    permission_classes = [IsModerator]

    @action(detail=True, methods=['post'], serializer_class=DisputeResolutionSerializer)
    @transaction.atomic
    def resolve(self, request, pk=None):
        initial = self.get_object()
        proposal = initial.exchange.proposal
        lock_items(proposal.offered_item_id, proposal.requested_item_id)
        exchange = Exchange.objects.select_for_update().get(pk=initial.exchange_id)
        dispute = Dispute.objects.select_for_update().get(pk=initial.pk)
        serializer = DisputeResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if dispute.status in ['resolved', 'closed'] or request.user.pk in [proposal.sender_id, proposal.recipient_id]:
            raise ValidationError('Cannot resolve this dispute.')
        dispute.status = 'resolved'
        dispute.resolution = serializer.validated_data['resolution']
        dispute.save()
        exchange.status = serializer.validated_data['outcome']
        exchange.completed_at = timezone.now() if exchange.status == 'completed' else None
        exchange.save()
        ItemListing.objects.filter(pk__in=[proposal.offered_item_id, proposal.requested_item_id]).update(
            status='exchanged' if exchange.status == 'completed' else 'paused')
        record(request.user, 'dispute.resolved', dispute, **serializer.validated_data)
        return Response(DisputeSerializer(dispute).data)


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ['id', 'actor', 'action', 'object_id', 'details', 'created_at']


class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.all()
    serializer_class = AuditSerializer
    permission_classes = [IsAdministrator]
