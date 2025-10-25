"""
Tests for Test and TestRegistration models
"""
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta
from decimal import Decimal

from tests.models import Test, TestRegistration
from accounts.models import User


class TestModelTests(TestCase):
    """Test 모델에 대한 단위 테스트"""

    def setUp(self):
        """각 테스트 전에 실행되는 설정"""
        self.now = timezone.now()
        self.test = Test.objects.create(
            title='Django Test',
            description='Django testing fundamentals',
            price=Decimal('50000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )

    def test_create_test_success(self):
        """성공: Test 객체 생성"""
        test = Test.objects.create(
            title='Python Test',
            description='Python basics',
            price=Decimal('45000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )
        self.assertEqual(test.title, 'Python Test')
        self.assertEqual(test.price, Decimal('45000.00'))
        self.assertIsNotNone(test.created_at)
        self.assertIsNotNone(test.updated_at)

    def test_create_test_with_null_description(self):
        """성공: description이 null인 Test 생성"""
        test = Test.objects.create(
            title='Minimal Test',
            description=None,
            price=Decimal('30000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=7)
        )
        self.assertIsNone(test.description)

    def test_test_str_representation(self):
        """성공: __str__ 메서드 테스트"""
        self.assertEqual(str(self.test), 'Django Test')

    def test_is_available_when_in_range(self):
        """성공: 현재 시간이 시험 기간 내에 있을 때"""
        self.assertTrue(self.test.is_available())

    def test_is_available_when_before_start(self):
        """실패: 시험 시작 전"""
        test = Test.objects.create(
            title='Future Test',
            description='Not started yet',
            price=Decimal('40000.00'),
            start_at=self.now + timedelta(days=5),
            end_at=self.now + timedelta(days=15)
        )
        self.assertFalse(test.is_available())

    def test_is_available_when_after_end(self):
        """실패: 시험 종료 후"""
        test = Test.objects.create(
            title='Past Test',
            description='Already finished',
            price=Decimal('35000.00'),
            start_at=self.now - timedelta(days=20),
            end_at=self.now - timedelta(days=5)
        )
        self.assertFalse(test.is_available())

    def test_is_available_at_exact_start_time(self):
        """엣지 케이스: 정확히 시작 시간"""
        test = Test.objects.create(
            title='Edge Case Test',
            description='Exact start time',
            price=Decimal('40000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=10)
        )
        self.assertTrue(test.is_available())

    def test_is_available_at_exact_end_time(self):
        """엣지 케이스: 정확히 종료 시간"""
        # 약간 미래 시간을 end_at로 설정 (테스트 실행 시간 고려)
        end_time = timezone.now() + timedelta(seconds=1)
        test = Test.objects.create(
            title='Edge Case Test 2',
            description='Exact end time',
            price=Decimal('40000.00'),
            start_at=end_time - timedelta(days=10),
            end_at=end_time
        )
        self.assertTrue(test.is_available())

    def test_auto_now_add_created_at(self):
        """성공: created_at 자동 설정"""
        test = Test.objects.create(
            title='Auto Timestamp Test',
            description='Testing timestamps',
            price=Decimal('30000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=7)
        )
        self.assertIsNotNone(test.created_at)
        self.assertAlmostEqual(
            test.created_at.timestamp(),
            self.now.timestamp(),
            delta=2  # 2초 이내 차이 허용
        )

    def test_auto_now_updated_at(self):
        """성공: updated_at 자동 업데이트"""
        old_updated_at = self.test.updated_at
        self.test.title = 'Updated Title'
        self.test.save()
        self.test.refresh_from_db()
        self.assertGreater(self.test.updated_at, old_updated_at)


class TestRegistrationModelTests(TestCase):
    """TestRegistration 모델에 대한 단위 테스트"""

    def setUp(self):
        """각 테스트 전에 실행되는 설정"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.test = Test.objects.create(
            title='Django Test',
            description='Django testing',
            price=Decimal('50000.00'),
            start_at=timezone.now() - timedelta(days=10),
            end_at=timezone.now() + timedelta(days=10)
        )

    def test_create_registration_success(self):
        """성공: TestRegistration 생성"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )
        self.assertEqual(registration.user, self.user)
        self.assertEqual(registration.test, self.test)
        self.assertEqual(registration.status, TestRegistration.Status.APPLIED)
        self.assertIsNotNone(registration.applied_at)

    def test_registration_str_representation(self):
        """성공: __str__ 메서드 테스트"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )
        expected = f"{self.user.email} - {self.test.title}"
        self.assertEqual(str(registration), expected)

    def test_default_status_is_applied(self):
        """성공: 기본 status가 APPLIED"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )
        self.assertEqual(registration.status, TestRegistration.Status.APPLIED)

    def test_status_choices(self):
        """성공: 모든 status choices 테스트"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        # APPLIED
        self.assertEqual(registration.status, 'applied')

        # COMPLETED
        registration.status = TestRegistration.Status.COMPLETED
        registration.completed_at = timezone.now()
        registration.save()
        self.assertEqual(registration.status, 'completed')

        # CANCELLED
        registration.status = TestRegistration.Status.CANCELLED
        registration.cancelled_at = timezone.now()
        registration.save()
        self.assertEqual(registration.status, 'cancelled')

    def test_unique_together_constraint(self):
        """실패: 동일한 user와 test로 중복 등록 시도"""
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        with self.assertRaises(IntegrityError):
            TestRegistration.objects.create(
                user=self.user,
                test=self.test
            )

    def test_different_users_same_test(self):
        """성공: 다른 사용자가 같은 시험에 등록"""
        user2 = User.objects.create_user(
            email='test2@example.com',
            username='testuser2',
            password='testpass123'
        )

        reg1 = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )
        reg2 = TestRegistration.objects.create(
            user=user2,
            test=self.test
        )

        self.assertNotEqual(reg1.user, reg2.user)
        self.assertEqual(reg1.test, reg2.test)

    def test_same_user_different_tests(self):
        """성공: 같은 사용자가 다른 시험에 등록"""
        test2 = Test.objects.create(
            title='Python Test',
            description='Python basics',
            price=Decimal('45000.00'),
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=30)
        )

        reg1 = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )
        reg2 = TestRegistration.objects.create(
            user=self.user,
            test=test2
        )

        self.assertEqual(reg1.user, reg2.user)
        self.assertNotEqual(reg1.test, reg2.test)

    def test_cascade_delete_user(self):
        """성공: User 삭제 시 연관된 Registration도 삭제"""
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        self.assertEqual(TestRegistration.objects.count(), 1)
        self.user.delete()
        self.assertEqual(TestRegistration.objects.count(), 0)

    def test_cascade_delete_test(self):
        """성공: Test 삭제 시 연관된 Registration도 삭제"""
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        self.assertEqual(TestRegistration.objects.count(), 1)
        self.test.delete()
        self.assertEqual(TestRegistration.objects.count(), 0)

    def test_nullable_timestamp_fields(self):
        """성공: completed_at, cancelled_at은 nullable"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        self.assertIsNone(registration.completed_at)
        self.assertIsNone(registration.cancelled_at)

    def test_completed_at_timestamp(self):
        """성공: completed_at 설정"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        now = timezone.now()
        registration.status = TestRegistration.Status.COMPLETED
        registration.completed_at = now
        registration.save()

        self.assertIsNotNone(registration.completed_at)
        self.assertEqual(registration.completed_at, now)

    def test_cancelled_at_timestamp(self):
        """성공: cancelled_at 설정"""
        registration = TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        now = timezone.now()
        registration.status = TestRegistration.Status.CANCELLED
        registration.cancelled_at = now
        registration.save()

        self.assertIsNotNone(registration.cancelled_at)
        self.assertEqual(registration.cancelled_at, now)

    def test_related_name_from_test(self):
        """성공: Test에서 registrations로 접근"""
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        self.assertEqual(self.test.registrations.count(), 1)
        self.assertEqual(
            self.test.registrations.first().user,
            self.user
        )

    def test_related_name_from_user(self):
        """성공: User에서 test_registrations로 접근"""
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        self.assertEqual(self.user.test_registrations.count(), 1)
        self.assertEqual(
            self.user.test_registrations.first().test,
            self.test
        )
