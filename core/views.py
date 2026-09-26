from django.db import connections
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import DashboardSerializer


def health(request):
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
        from django.core.cache import cache
        cache.set('health', True, timeout=10)
        if not cache.get('health'):
            raise RuntimeError('Cache unavailable')
    except Exception:
        return JsonResponse({'status': 'unhealthy'}, status=503)
    return JsonResponse({'status': 'healthy'})


class DashboardView(APIView):
    serializer_class = DashboardSerializer
    def get(self, request):
        from exchanges.models import ExchangeProposal, Exchange
        from django.utils import timezone
        proposals = ExchangeProposal.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        exchanges = Exchange.objects.filter(Q(proposal__sender=request.user) | Q(proposal__recipient=request.user))
        return Response({'active_listings': request.user.listings.filter(status='active').count(),
            'pending_offers': proposals.filter(status='pending', expires_at__gt=timezone.now()).count(),
            'active_exchanges': exchanges.filter(status='agreed').count(),
            'completed_exchanges': exchanges.filter(status='completed').count(),
            'unread_notifications': request.user.notifications.filter(read_at__isnull=True).count()})
