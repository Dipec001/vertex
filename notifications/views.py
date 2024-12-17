from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin.messaging import Message, Notification, send
from rest_framework.permissions import AllowAny

class SendNotificationAPIView(APIView): 
    permission_classes = [AllowAny] 
    def post(self, request, *args, **kwargs): 
        fcm_token = request.data.get("fcm_token") 
        title = request.data.get("title") 
        body = request.data.get("body") 
        data = request.data.get("data", {}) 
        image_url = request.data.get("image_url", None) 
        if not fcm_token or not title or not body: 
            return Response({"error": "FCM token, title, and body are required."}, status=status.HTTP_400_BAD_REQUEST) 
        try: 
            message = Message( notification=Notification( title=title, body=body, image=image_url ), 
                              data=data, token=fcm_token ) 
            response = send(message) 
            return Response({"success": True, "response": response}) 
        except Exception as e: 
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

