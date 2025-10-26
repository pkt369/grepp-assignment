from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from .models import Course


@receiver(post_save, sender=Course)
def update_search_vector(sender, instance, created, **kwargs):
    """
    Course 모델 저장 후에 search_vector 필드를 자동으로 업데이트합니다.

    - title 필드: weight='A' (높은 우선순위)
    - description 필드: weight='B' (낮은 우선순위)

    Note: post_save를 사용하여 INSERT 후 UPDATE로 search_vector 설정
    데이터베이스 레벨에서 트리거로 대체 가능
    """
    # 무한 루프 방지: update_fields로 search_vector만 업데이트하는 경우 스킵
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'search_vector' in update_fields:
        return

    # search_vector 업데이트
    Course.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector('title', weight='A', config='simple') +
            SearchVector('description', weight='B', config='simple')
        )
    )
