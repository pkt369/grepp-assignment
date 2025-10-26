from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from courses.models import Course


class Command(BaseCommand):
    help = '기존 Course 데이터의 search_vector 필드를 일괄 업데이트합니다'

    def handle(self, *args, **options):
        """
        모든 Course 객체의 search_vector를 일괄 업데이트

        - 배치 단위로 처리 (10,000개씩)
        - 진행 상황 출력
        """
        self.stdout.write('search_vector 업데이트를 시작합니다...')

        # 전체 개수 확인
        total_count = Course.objects.count()
        self.stdout.write(f'총 {total_count}개의 Course 데이터를 업데이트합니다.')

        if total_count == 0:
            self.stdout.write(self.style.WARNING('업데이트할 데이터가 없습니다.'))
            return

        # 배치 크기
        batch_size = 10000
        updated_count = 0

        # 배치 단위로 처리
        course_ids = Course.objects.values_list('id', flat=True)
        batches = [course_ids[i:i + batch_size] for i in range(0, len(course_ids), batch_size)]

        for i, batch_ids in enumerate(batches, 1):
            # 배치 업데이트
            Course.objects.filter(id__in=batch_ids).update(
                search_vector=(
                    SearchVector('title', weight='A', config='simple') +
                    SearchVector('description', weight='B', config='simple')
                )
            )

            updated_count += len(batch_ids)
            self.stdout.write(
                f'배치 {i}/{len(batches)} 완료: {updated_count}/{total_count} 업데이트됨'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ 완료! 총 {updated_count}개의 search_vector가 업데이트되었습니다.'
            )
        )
