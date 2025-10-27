from django.db import models
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    search_vector = SearchVectorField(null=True, blank=True)
    registration_count = models.IntegerField(default=0, db_index=True)

    class Meta:
        db_table = 'courses'
        indexes = [
            models.Index(fields=['start_at', 'end_at'], name='idx_course_dates'),
            models.Index(fields=['-created_at'], name='idx_course_created'),
            models.Index(fields=['start_at', 'end_at', '-created_at'], name='idx_course_composite'),
            GinIndex(fields=['search_vector'], name='idx_course_search'),
        ]

    def is_available(self):
        now = timezone.now()
        return self.start_at <= now <= self.end_at

    def __str__(self):
        return self.title


class CourseRegistration(models.Model):
    class Status(models.TextChoices):
        ENROLLED = 'enrolled', 'Enrolled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='course_registrations'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ENROLLED
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'course_registrations'
        unique_together = [['user', 'course']]
        indexes = [
            models.Index(fields=['user', 'course'], name='idx_course_reg_unique'),
            models.Index(fields=['status'], name='idx_course_reg_status'),
            models.Index(fields=['user'], name='idx_course_reg_user'),
            models.Index(fields=['course'], name='idx_course_reg_course'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"
