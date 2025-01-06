from rest_framework import serializers
from .models import Ticket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    is_current_user = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = ['id', 'message', 'attachment', 'created_at', 'sender', 'sender_name', 'is_current_user']
        read_only_fields = ['sender', 'is_current_user']

    def get_is_current_user(self, obj):
        # We don't need to pass the request here anymore
        if obj.sender.is_staff or obj.sender.is_superuser:
            return False  # If the sender is a staff or superuser, it's false
        return True  # Otherwise, it's true
        


class TicketSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    creator_fullname = serializers.SerializerMethodField()
    creator_email = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    last_response = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'status',
                  'created_at', 'created_by', 'creator_fullname', 'creator_email', 'created_by_name',
                  'is_individual', 'company', 'company_name', "assigned_to", "assigned_to_name", "last_response"]
        read_only_fields = ['created_by', 'company', 'created_at', 'last_response']

    def get_creator_fullname(self, obj: Ticket):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"

    def get_creator_email(self, obj: Ticket):
        return obj.created_by.email

    def get_last_response(self, obj):
        last_message = obj.messages.order_by("-created_at").first()
        return last_message.created_at if last_message else None