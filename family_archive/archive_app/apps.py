from django.apps import AppConfig


class ArchiveAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'archive_app'
    def ready(self):
        from . import signals
