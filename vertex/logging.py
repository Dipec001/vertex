# import logging
# from django.utils.log import AdminEmailHandler
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
# import datetime
# import os

# class EmailHandler(AdminEmailHandler):
#     def emit(self, record):
#         """
#         This sends a brief email notification for log records.
#         """
#         try:
#             current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             subject = f"Notification: {record.levelname}"
#             message = f"\nA new error has been logged in your Django application at {current_time}\n"

#             self.send_mail(subject, message, fail_silently=True)
#         except Exception:
#             self.handleError(record)

# class SlackHandler(logging.Handler):
#     def __init__(self, token, channel):
#         super().__init__()
#         self.client = WebClient(token=token)
#         self.channel = channel

#     def emit(self, record):
#         message = self.format(record)
#         try:
#             response = self.client.chat_postMessage(
#                 channel=self.channel,
#                 text=message
#             )
#         except SlackApiError as e:
#             print(f"Error sending message to Slack: {e.response['error']}")

# # Setup logging configuration
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'class': 'logging.StreamHandler',
#         },
#         'mail_admins': {
#             'level': 'ERROR',
#             'class': 'vertex.logging.EmailHandler',
#         },
#         'slack': {
#             'level': 'ERROR',
#             'class': 'vertex.logging.SlackHandler',
#             'token': os.getenv('SLACK_TOKEN'),
#             'channel': 'errors',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console', 'mail_admins', 'slack'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#         'vertex_error': {
#             'handlers': ['console', 'mail_admins', 'slack'],
#             'level': 'ERROR',
#             'propagate': True,
#         },
#         'vertex_info': {
#             'handlers': ['console'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#     },
# }
