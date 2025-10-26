import time
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from tests.models import Test


class Command(BaseCommand):
    help = 'Create seed tests for performance testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1000000,
            help='Number of tests to create (default: 1,000,000)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10000,
            help='Batch size for bulk creation (default: 10,000)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing tests before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        batch_size = options['batch_size']
        clear = options['clear']

        start_time = time.time()

        self.stdout.write(self.style.WARNING('\n=== 시험 생성 시작 ==='))

        # Clear existing tests if requested
        if clear:
            self.stdout.write('기존 시험 삭제 중...')
            Test.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ 기존 시험 삭제 완료'))

        # Create tests in batches
        self.stdout.write(f'{count:,}개의 시험 생성 중...\n')

        now = timezone.now()
        created_count = 0

        # Prepare template data
        adjectives = ['기본', '고급', '실전', '핵심', '완벽', '전문', '실무', '입문', '심화', '마스터']
        subjects = ['Python', 'Django', 'React', 'JavaScript', 'SQL', 'Java', 'Spring', 'Docker', 'AWS', 'Git']

        for batch_start in range(0, count, batch_size):
            batch_tests = []
            batch_end = min(batch_start + batch_size, count)

            for i in range(batch_start, batch_end):
                # Generate test data
                adj = adjectives[i % len(adjectives)]
                subj = subjects[i % len(subjects)]
                title = f'{adj} {subj} 시험 {i + 1}'
                description = f'{title}에 대한 상세 설명입니다. 본 시험은 {subj} 기술에 대한 이해도를 평가합니다.'

                # Random price between 10,000 and 100,000
                price = random.randint(100, 1000) * 100

                # Random start time (past 30 days to future 30 days)
                start_offset = random.randint(-30, 30)
                start_at = now + timedelta(days=start_offset, hours=random.randint(0, 23))

                # End time is 1-7 days after start
                end_offset = random.randint(1, 7)
                end_at = start_at + timedelta(days=end_offset)

                batch_tests.append(Test(
                    title=title,
                    description=description,
                    price=price,
                    start_at=start_at,
                    end_at=end_at
                ))

            # Bulk create batch
            Test.objects.bulk_create(batch_tests)
            created_count += len(batch_tests)

            # Clear batch list to free memory
            batch_tests.clear()

            # Show progress every 10%
            progress = (created_count / count) * 100
            elapsed = time.time() - start_time

            if created_count % (batch_size * 10) == 0 or created_count == count:
                self.stdout.write(
                    f'{created_count:,} / {count:,} ({progress:.0f}%) - 경과: {self._format_time(elapsed)}'
                )

        # Calculate total elapsed time
        total_elapsed = time.time() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ 시험 {count:,}개 생성 완료 (소요 시간: {self._format_time(total_elapsed)})\n'
            )
        )

    def _format_time(self, seconds):
        """Format seconds into human-readable time"""
        if seconds < 60:
            return f'{seconds:.1f}초'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f'{minutes}분 {secs}초'
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f'{hours}시간 {minutes}분'
