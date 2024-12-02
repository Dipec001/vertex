from django.utils.log import AdminEmailHandler
import datetime


class EmailHandler(AdminEmailHandler):
    def emit(self, record):
        """
        This sends a brief email notification for log records.
        """
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            subject = f"Notification: {record.levelname}"
            message = f"\nA new error has been logged in your Django application at {current_time}\n"

            self.send_mail(subject, message, fail_silently=True)
        except Exception:
            self.handleError(record)
