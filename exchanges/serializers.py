from rest_framework import serializers
from .models import ExchangeProposal, Exchange


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeProposal
        fields = ['id', 'sender', 'recipient', 'offered_item', 'requested_item', 'message', 'parent', 'status', 'expires_at', 'created_at']
        read_only_fields = ['sender', 'recipient', 'parent', 'status', 'expires_at', 'created_at']


class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = ['id', 'proposal', 'status', 'sender_confirmed_at', 'recipient_confirmed_at',
                  'completed_at', 'meeting_details', 'created_at']
        read_only_fields = fields
