from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        TEST = 'test', 'Test'
        COURSE = 'course', 'Course'

    class Status(models.TextChoices):
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        KAKAOPAY = 'kakaopay', 'KakaoPay'
        CARD = 'card', 'Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)

    # GenericForeignKey for Test or Course
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PaymentMethod.choices)
    external_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAID)
    refund_reason = models.TextField(null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_payment_user_status'),
            models.Index(fields=['paid_at'], name='idx_payment_paid_at'),
            models.Index(fields=['status', 'paid_at'], name='idx_payment_status_date'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.payment_type} - {self.amount}"
