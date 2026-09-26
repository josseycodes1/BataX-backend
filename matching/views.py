from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from accounts.models import Block
from listings.models import ItemListing
from listings.serializers import ListingSerializer


def preference_score(source, target):
    best = 0
    for want in source.wants.all():
        if want.category_id and want.category_id != target.category_id:
            continue
        if want.brand and want.brand.casefold() != target.brand.casefold():
            continue
        if want.model and want.model.casefold() != target.model.casefold():
            continue
        if want.title and want.title.casefold() not in target.title.casefold():
            continue
        best = max(best, 3 if want.title or want.model else 2)
    return best or (1 if source.open_to_offers else 0)


class MatchView(generics.GenericAPIView):
    serializer_class = ListingSerializer

    def get(self, request):
        own = ItemListing.objects.filter(owner=request.user, status='active').prefetch_related('wants')
        if request.query_params.get('listing'):
            from django.shortcuts import get_object_or_404
            own = [get_object_or_404(own, pk=request.query_params['listing'])]
        blocked = Block.objects.filter(Q(user=request.user) | Q(blocked_user=request.user))
        excluded = {request.user.pk}
        for block in blocked:
            excluded.update([block.user_id, block.blocked_user_id])
        candidates = ItemListing.objects.filter(status='active', owner__is_active=True,
            owner__is_identity_verified=True, category__is_prohibited=False).exclude(owner_id__in=excluded).select_related('owner__profile').prefetch_related('wants', 'images')
        if request.query_params.get('city'):
            candidates = candidates.filter(city__iexact=request.query_params['city'])
        # Paginate the candidate pool before computing pairs to bound response work.
        page = self.paginate_queryset(candidates)
        results = []
        for candidate in page:
            for listing in own:
                a, b = preference_score(listing, candidate), preference_score(candidate, listing)
                if a and b:
                    kind = 'exact_reciprocal' if a == b == 3 else 'flexible_reciprocal' if min(a, b) >= 2 else 'one_way'
                    results.append({'listing': str(listing.pk), 'candidate': ListingSerializer(candidate).data,
                                    'type': kind, 'score': a + b})
        results.sort(key=lambda x: x['score'], reverse=True)
        return self.get_paginated_response(results)
