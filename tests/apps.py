from django.apps import AppConfig


class TestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tests'

    def ready(self):
        """
        Django 시작 시 Signal을 자동으로 등록합니다.
        """
        import tests.signals  # noqa
