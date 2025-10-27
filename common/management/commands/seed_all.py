import time
import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from accounts.models import User
from tests.models import Test, TestRegistration
from courses.models import Course, CourseRegistration
from payments.models import Payment


class Command(BaseCommand):
    help = 'Run all seed commands to populate the database with test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )
        parser.add_argument(
            '--tests',
            type=int,
            default=1000000,
            help='Number of tests to create (default: 1,000,000)'
        )
        parser.add_argument(
            '--courses',
            type=int,
            default=1000000,
            help='Number of courses to create (default: 1,000,000)'
        )
        parser.add_argument(
            '--registrations-per-user',
            type=int,
            default=5,
            help='Number of registrations per user (default: 5)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing data before seeding'
        )
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Skip user seeding'
        )
        parser.add_argument(
            '--skip-tests',
            action='store_true',
            help='Skip test seeding'
        )
        parser.add_argument(
            '--skip-courses',
            action='store_true',
            help='Skip course seeding'
        )
        parser.add_argument(
            '--skip-registrations',
            action='store_true',
            help='Skip registration/payment seeding'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Disable all logging output (only show summary)'
        )

    def handle(self, *args, **options):
        # Always disable logging during seed operations
        # Set all loggers to CRITICAL level (effectively disabling INFO/WARNING/ERROR logs)
        logging.disable(logging.CRITICAL)
        # Also disable Django's SQL query logging
        logging.getLogger('django.db.backends').setLevel(logging.CRITICAL)

        total_start_time = time.time()

        self.stdout.write(
            self.style.WARNING(
                '\n' + '='*50 + '\n' +
                '   Seed 데이터 생성 시작\n' +
                '='*50 + '\n'
            )
        )

        step_times = {}

        # Always set verbosity to 0 to disable output from sub-commands
        verbosity = 0

        # Step 1: Seed Users
        if not options['skip_users']:
            step_start = time.time()
            call_command(
                'seed_users',
                count=options['users'],
                clear=options['clear'],
                verbosity=verbosity
            )
            step_times['users'] = time.time() - step_start

        # Step 2: Seed Tests
        if not options['skip_tests']:
            step_start = time.time()
            call_command(
                'seed_tests',
                count=options['tests'],
                batch_size=10000,
                clear=options['clear'],
                verbosity=verbosity
            )
            step_times['tests'] = time.time() - step_start

        # Step 3: Seed Courses
        if not options['skip_courses']:
            step_start = time.time()
            call_command(
                'seed_courses',
                count=options['courses'],
                batch_size=10000,
                clear=options['clear'],
                verbosity=verbosity
            )
            step_times['courses'] = time.time() - step_start

        # Step 4: Seed Registrations and Payments
        if not options['skip_registrations']:
            step_start = time.time()
            call_command(
                'seed_registrations',
                per_user=options['registrations_per_user'],
                clear=options['clear'],
                verbosity=verbosity
            )
            step_times['registrations'] = time.time() - step_start

        # Calculate total time
        total_elapsed = time.time() - total_start_time

        # Get final counts
        user_count = User.objects.count()
        test_count = Test.objects.count()
        course_count = Course.objects.count()
        test_reg_count = TestRegistration.objects.count()
        course_reg_count = CourseRegistration.objects.count()
        payment_count = Payment.objects.count()

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                '\n' + '='*50 + '\n' +
                '   Seed 데이터 생성 완료\n' +
                '='*50 + '\n'
            )
        )

        self.stdout.write(self.style.SUCCESS('\n📊 생성된 데이터:'))
        self.stdout.write(f'  • 사용자: {user_count:,}명')
        self.stdout.write(f'  • 시험: {test_count:,}개')
        self.stdout.write(f'  • 수업: {course_count:,}개')
        self.stdout.write(f'  • 시험 응시: {test_reg_count:,}건')
        self.stdout.write(f'  • 수업 수강: {course_reg_count:,}건')
        self.stdout.write(f'  • 결제: {payment_count:,}건')

        self.stdout.write(self.style.SUCCESS('\n⏱️  단계별 소요 시간:'))
        for step, duration in step_times.items():
            self.stdout.write(f'  • {step}: {self._format_time(duration)}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ 총 소요 시간: {self._format_time(total_elapsed)}\n'
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
