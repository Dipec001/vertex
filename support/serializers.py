from rest_framework import serializers
from .models import Ticket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'message', 'attachment', 'created_at', 'sender', 'sender_name']
        read_only_fields = ['sender']


class TicketSerializer(serializers.ModelSerializer):
    # messages = TicketMessageSerializer(many=True, read_only=True)
    # created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    # creator_fullname = serializers.SerializerMethodField()
    # creator_email = serializers.SerializerMethodField()
    # assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    # last_response = serializers.SerializerMethodField()
    # company_name = serializers.CharField(source='company.name', read_only=True)
    last_response = serializers.SerializerMethodField()
    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'status', 'created_at', 'last_response']
        read_only_fields = ['created_at', 'last_response']

    # def get_creator_fullname(self, obj: Ticket):
    #     return f"{obj.created_by.first_name} {obj.created_by.last_name}"

    # def get_creator_email(self, obj: Ticket):
    #     return obj.created_by.email

    def get_last_response(self, obj):
        last_message = obj.messages.order_by("-created_at").first()
        return last_message.created_at if last_message else None