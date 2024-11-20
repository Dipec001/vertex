from django.apps import AppConfig


class MyappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "myapp"

    def ready(self):
        # Import your signals to ensure they're connected
        import myapp.signals
        import myapp.websocket_signals
