from rest_framework import serializers, viewsets
from rest_framework.permissions import AllowAny
from core.permissions import IsAdministrator
from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'country', 'state', 'city']


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by('country', 'state', 'city')
    serializer_class = LocationSerializer
    filterset_fields = ['country', 'state']
    search_fields = ['city', 'state']

    def get_permissions(self):
        return [AllowAny()] if self.action in ['list', 'retrieve'] else [IsAdministrator()]
