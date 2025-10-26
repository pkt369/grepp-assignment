from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self):
        """앱 초기화 시 signal 등록"""
        import payments.signals  # noqa
