from django.apps import AppConfig


class GisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gis"
    verbose_name = "GIS & Pariwisata"

    def ready(self):
        from apps.gis import signals  # noqa: F401

        signals.connect_signals()
