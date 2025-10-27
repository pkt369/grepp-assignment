from django.db import models
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Test(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        db_table = 'tests'
        indexes = [
            models.Index(fields=['start_at', 'end_at'], name='idx_test_dates'),
            models.Index(fields=['-created_at'], name='idx_test_created'),
            models.Index(fields=['start_at', 'end_at', '-created_at'], name='idx_test_composite'),
            GinIndex(fields=['search_vector'], name='idx_test_search'),
        ]

    def is_available(self):
        now = timezone.now()
        return self.start_at <= now <= self.end_at

    def __str__(self):
        return self.title


class TestRegistration(models.Model):
    class Status(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='test_registrations'
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'test_registrations'
        unique_together = [['user', 'test']]
        indexes = [
            models.Index(fields=['user', 'test'], name='idx_test_reg_unique'),
            models.Index(fields=['status'], name='idx_test_reg_status'),
            models.Index(fields=['user'], name='idx_test_reg_user'),
            models.Index(fields=['test'], name='idx_test_reg_test'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.test.title}"
