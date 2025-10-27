"""
Management command to initialize registration counts.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from tests.models import Test
from courses.models import Course
from common.redis_client import get_redis_client


class Command(BaseCommand):
    help = 'Initialize registration counts for all tests and courses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for processing (default: 1000)',
        )
        parser.add_argument(
            '--clear-redis',
            action='store_true',
            help='Clear Redis updated_ids sets',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        clear_redis = options['clear_redis']

        self.stdout.write(self.style.SUCCESS('Starting count initialization...'))

        # Initialize test counts
        self.init_test_counts(batch_size)

        # Initialize course counts
        self.init_course_counts(batch_size)

        # Clear Redis if requested
        if clear_redis:
            self.clear_redis_sets()

        self.stdout.write(self.style.SUCCESS('Count initialization completed!'))

    def init_test_counts(self, batch_size):
        """Initialize registration counts for all tests."""
        self.stdout.write('Initializing test registration counts...')

        # Get all tests with their actual registration counts
        tests = Test.objects.annotate(
            actual_count=Count('registrations')
        ).values('id', 'title', 'registration_count', 'actual_count')

        total_tests = tests.count()
        updated_count = 0

        self.stdout.write(f'Found {total_tests} tests to process')

        for i, test in enumerate(tests, 1):
            # Update if count differs
            if test['registration_count'] != test['actual_count']:
                Test.objects.filter(id=test['id']).update(
                    registration_count=test['actual_count']
                )
                updated_count += 1
                self.stdout.write(
                    f"Updated test '{test['title']}' (ID: {test['id']}): "
                    f"{test['registration_count']} → {test['actual_count']}"
                )

            # Progress indicator
            if i % 100 == 0:
                self.stdout.write(f'Processed {i}/{total_tests} tests...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Test counts initialized: {updated_count} updated, '
                f'{total_tests - updated_count} already correct'
            )
        )

    def init_course_counts(self, batch_size):
        """Initialize enrollment counts for all courses."""
        self.stdout.write('Initializing course enrollment counts...')

        # Get all courses with their actual enrollment counts
        courses = Course.objects.annotate(
            actual_count=Count('registrations')
        ).values('id', 'title', 'registration_count', 'actual_count')

        total_courses = courses.count()
        updated_count = 0

        self.stdout.write(f'Found {total_courses} courses to process')

        for i, course in enumerate(courses, 1):
            # Update if count differs
            if course['registration_count'] != course['actual_count']:
                Course.objects.filter(id=course['id']).update(
                    registration_count=course['actual_count']
                )
                updated_count += 1
                self.stdout.write(
                    f"Updated course '{course['title']}' (ID: {course['id']}): "
                    f"{course['registration_count']} → {course['actual_count']}"
                )

            # Progress indicator
            if i % 100 == 0:
                self.stdout.write(f'Processed {i}/{total_courses} courses...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Course counts initialized: {updated_count} updated, '
                f'{total_courses - updated_count} already correct'
            )
        )

    def clear_redis_sets(self):
        """Clear Redis updated_ids sets."""
        self.stdout.write('Clearing Redis sets...')

        try:
            redis_client = get_redis_client()
            if not redis_client:
                self.stdout.write(
                    self.style.WARNING('Failed to get Redis client, skipping Redis clear')
                )
                return

            # Clear test and course updated_ids sets
            redis_client.delete('test:updated_ids')
            redis_client.delete('course:updated_ids')

            self.stdout.write(self.style.SUCCESS('Redis sets cleared'))

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Failed to clear Redis sets: {e}')
            )
