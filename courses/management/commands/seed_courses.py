import time
import random
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from courses.models import Course


class Command(BaseCommand):
    help = 'Create seed courses for performance testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1000000,
            help='Number of courses to create (default: 1,000,000)'
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
            help='Delete existing courses before creating new ones'
        )

    def handle(self, *args, **options):
        # Disable logging during seed operations
        logging.disable(logging.CRITICAL)
        count = options['count']
        batch_size = options['batch_size']
        clear = options['clear']

        start_time = time.time()

        self.stdout.write(self.style.WARNING('\n=== 수업 생성 시작 ==='))

        # Clear existing courses if requested
        if clear:
            self.stdout.write('기존 수업 삭제 중...')
            Course.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ 기존 수업 삭제 완료'))

        # Create courses in batches
        self.stdout.write(f'{count:,}개의 수업 생성 중...\n')

        now = timezone.now()
        created_count = 0

        # Prepare template data
        levels = ['입문', '초급', '중급', '고급', '전문가']
        subjects = ['Python', 'Django', 'React', 'JavaScript', 'SQL', 'Java', 'Spring', 'Docker', 'Kubernetes', 'AWS']
        types = ['기초', '실전', '프로젝트', '심화', '특강']

        for batch_start in range(0, count, batch_size):
            batch_courses = []
            batch_end = min(batch_start + batch_size, count)

            for i in range(batch_start, batch_end):
                # Generate course data
                level = levels[i % len(levels)]
                subj = subjects[i % len(subjects)]
                typ = types[i % len(types)]
                title = f'{level} {subj} {typ} 과정 {i + 1}'
                description = f'{title}에 대한 상세 설명입니다. 본 과정은 {subj} 기술을 {level} 수준에서 학습합니다.'

                # Random price between 10,000 and 100,000
                price = random.randint(100, 1000) * 100

                # Random start time (past 30 days to future 30 days)
                start_offset = random.randint(-30, 30)
                start_at = now + timedelta(days=start_offset, hours=random.randint(0, 23))

                # End time is 7-90 days after start (courses are longer)
                end_offset = random.randint(7, 90)
                end_at = start_at + timedelta(days=end_offset)

                batch_courses.append(Course(
                    title=title,
                    description=description,
                    price=price,
                    start_at=start_at,
                    end_at=end_at
                ))

            # Bulk create batch
            Course.objects.bulk_create(batch_courses)
            created_count += len(batch_courses)

            # Clear batch list to free memory
            batch_courses.clear()

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
                f'\n✓ 수업 {count:,}개 생성 완료 (소요 시간: {self._format_time(total_elapsed)})\n'
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
