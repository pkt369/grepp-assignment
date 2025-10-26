import time
import random
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from accounts.models import User
from tests.models import Test, TestRegistration
from courses.models import Course, CourseRegistration
from payments.models import Payment


class Command(BaseCommand):
    help = 'Create seed registrations and payments for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-user',
            type=int,
            default=5,
            help='Number of registrations per user (default: 5)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing registrations and payments before creating new ones'
        )

    def handle(self, *args, **options):
        per_user = options['per_user']
        clear = options['clear']

        start_time = time.time()

        self.stdout.write(self.style.WARNING('\n=== 등록 및 결제 데이터 생성 시작 ==='))

        # Clear existing data if requested
        if clear:
            self.stdout.write('기존 데이터 삭제 중...')
            Payment.objects.all().delete()
            TestRegistration.objects.all().delete()
            CourseRegistration.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ 기존 데이터 삭제 완료'))

        # Get all users
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('Error: No users found. Please run seed_users first.'))
            return

        # Get sample tests and courses
        tests = list(Test.objects.all()[:1000])  # Get first 1000 tests
        courses = list(Course.objects.all()[:1000])  # Get first 1000 courses

        if not tests:
            self.stdout.write(self.style.ERROR('Error: No tests found. Please run seed_tests first.'))
            return

        if not courses:
            self.stdout.write(self.style.ERROR('Error: No courses found. Please run seed_courses first.'))
            return

        self.stdout.write(f'사용자 {len(users)}명에 대한 등록/결제 데이터 생성 중...\n')

        # Get content types
        test_content_type = ContentType.objects.get_for_model(Test)
        course_content_type = ContentType.objects.get_for_model(Course)

        # Payment methods
        payment_methods = [
            Payment.PaymentMethod.KAKAOPAY,
            Payment.PaymentMethod.CARD,
            Payment.PaymentMethod.BANK_TRANSFER
        ]

        # Counters
        test_reg_count = 0
        course_reg_count = 0
        payment_count = 0

        # Create registrations and payments for each user
        for user in users:
            # Randomly select tests and courses for this user
            num_tests = random.randint(1, min(per_user, len(tests)))
            num_courses = random.randint(1, min(per_user, len(courses)))

            selected_tests = random.sample(tests, num_tests)
            selected_courses = random.sample(courses, num_courses)

            # Create test registrations and payments
            test_registrations = []
            test_payments = []

            for test in selected_tests:
                # Create registration
                status = random.choice([
                    TestRegistration.Status.APPLIED,
                    TestRegistration.Status.COMPLETED,
                    TestRegistration.Status.CANCELLED
                ])
                registration = TestRegistration(
                    user=user,
                    test=test,
                    status=status
                )
                test_registrations.append(registration)

                # Create payment
                payment_status = Payment.Status.PAID if status != TestRegistration.Status.CANCELLED else Payment.Status.CANCELLED
                payment = Payment(
                    user=user,
                    payment_type=Payment.PaymentType.TEST,
                    content_type=test_content_type,
                    object_id=test.id,
                    amount=test.price,
                    payment_method=random.choice(payment_methods),
                    status=payment_status,
                    external_transaction_id=f'TEST-{user.id}-{test.id}-{int(time.time())}'
                )
                test_payments.append(payment)

            # Bulk create test registrations and payments
            TestRegistration.objects.bulk_create(test_registrations, ignore_conflicts=True)
            Payment.objects.bulk_create(test_payments)
            test_reg_count += len(test_registrations)
            payment_count += len(test_payments)

            # Create course registrations and payments
            course_registrations = []
            course_payments = []

            for course in selected_courses:
                # Create registration
                status = random.choice([
                    CourseRegistration.Status.ENROLLED,
                    CourseRegistration.Status.COMPLETED,
                    CourseRegistration.Status.CANCELLED
                ])
                registration = CourseRegistration(
                    user=user,
                    course=course,
                    status=status
                )
                course_registrations.append(registration)

                # Create payment
                payment_status = Payment.Status.PAID if status != CourseRegistration.Status.CANCELLED else Payment.Status.CANCELLED
                payment = Payment(
                    user=user,
                    payment_type=Payment.PaymentType.COURSE,
                    content_type=course_content_type,
                    object_id=course.id,
                    amount=course.price,
                    payment_method=random.choice(payment_methods),
                    status=payment_status,
                    external_transaction_id=f'COURSE-{user.id}-{course.id}-{int(time.time())}'
                )
                course_payments.append(payment)

            # Bulk create course registrations and payments
            CourseRegistration.objects.bulk_create(course_registrations, ignore_conflicts=True)
            Payment.objects.bulk_create(course_payments)
            course_reg_count += len(course_registrations)
            payment_count += len(course_payments)

        # Calculate elapsed time
        elapsed = time.time() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ 등록/결제 데이터 생성 완료:\n'
                f'  - 시험 응시: {test_reg_count}건\n'
                f'  - 수업 수강: {course_reg_count}건\n'
                f'  - 결제: {payment_count}건\n'
                f'  소요 시간: {elapsed:.2f}초\n'
            )
        )
