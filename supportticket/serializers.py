from rest_framework import serializers
from .models import SupportTicket, SupportMessage

class SupportTicketSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = ['id', 'user', 'title', 'description', 'created_at', 'status']




class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = ['id', 'ticket', 'is_current_user', 'message', 'message_time', 'support_staff_name']

    def create(self, validated_data):
        request = self.context['request']
        
        # Automatically set `is_current_user` based on the user's role
        if request.user.is_staff or request.user.is_superuser:
            validated_data['is_current_user'] = False
            validated_data['support_staff_name'] = "Activity Rewards Support"
        else:
            validated_data['is_current_user'] = True
            validated_data['support_staff_name'] = ""  # Default for regular users
        
        return super().create(validated_data)
