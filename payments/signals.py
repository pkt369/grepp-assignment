from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from payments.models import Payment


@receiver(post_save, sender=Payment)
def update_payment_search_vector(sender, instance, created, **kwargs):
    """
    Payment 저장 후 search_vector 필드를 자동으로 업데이트

    - target (Test/Course)의 title을 기반으로 검색 가능하게 함
    - GenericForeignKey를 통해 연결된 대상의 title 사용

    Note: post_save를 사용하여 INSERT 후 UPDATE로 search_vector 설정
    """
    # 무한 루프 방지
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'search_vector' in update_fields:
        return

    # target의 title 가져오기
    target_title = ''
    if instance.target:
        target_title = getattr(instance.target, 'title', '')

    # search_vector 업데이트
    if target_title:
        Payment.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector('payment_type', weight='B', config='simple') +
                         SearchVector('status', weight='B', config='simple')
        )
    else:
        # target이 없으면 payment_type, status만으로 검색
        Payment.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector('payment_type', weight='B', config='simple') +
                         SearchVector('status', weight='B', config='simple')
        )
