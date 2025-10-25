from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'

    def ready(self):
        """앱 준비 완료 시 signals를 import합니다."""
        import courses.signals
