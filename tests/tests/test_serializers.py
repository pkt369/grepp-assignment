"""
Tests for TestSerializer
"""
from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from tests.models import Test, TestRegistration
from tests.serializers import TestSerializer
from accounts.models import User


class TestSerializerTests(TestCase):
    """TestSerializer에 대한 단위 테스트"""

    def setUp(self):
        """각 테스트 전에 실행되는 설정"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )

        self.now = timezone.now()
        self.test = Test.objects.create(
            title='Django Test',
            description='Django testing fundamentals',
            price=Decimal('50000.00'),
            start_at=self.now - timedelta(days=10),
            end_at=self.now + timedelta(days=10)
        )

    def test_serializer_contains_expected_fields(self):
        """성공: Serializer가 모든 필드를 포함"""
        request = self.factory.get('/fake-path')
        request.user = self.user

        # Annotate registration_count
        self.test.registration_count = 0

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        data = serializer.data
        expected_fields = [
            'id', 'title', 'description', 'price',
            'start_at', 'end_at', 'created_at',
            'is_registered', 'registration_count'
        ]

        for field in expected_fields:
            self.assertIn(field, data)

    def test_is_registered_true_when_user_registered(self):
        """성공: 사용자가 등록한 경우 is_registered=True"""
        # 사용자 등록
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        self.assertTrue(serializer.data['is_registered'])

    def test_is_registered_false_when_user_not_registered(self):
        """성공: 사용자가 등록하지 않은 경우 is_registered=False"""
        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        self.assertFalse(serializer.data['is_registered'])

    def test_is_registered_false_for_unauthenticated_user(self):
        """성공: 미인증 사용자의 경우 is_registered=False"""
        request = self.factory.get('/fake-path')
        request.user = None

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        self.assertFalse(serializer.data['is_registered'])

    def test_is_registered_false_when_no_request_context(self):
        """성공: request context가 없는 경우 is_registered=False"""
        serializer = TestSerializer(self.test)
        self.assertFalse(serializer.data['is_registered'])

    def test_is_registered_uses_annotated_flag(self):
        """성공: annotated is_registered_flag가 있으면 그것을 사용"""
        # TestRegistration 생성
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        # is_registered_flag를 annotated 값으로 설정
        self.test.is_registered_flag = True

        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        # annotated 값이 사용되어야 함
        self.assertTrue(serializer.data['is_registered'])

    def test_is_registered_fallback_to_db_query(self):
        """성공: is_registered_flag가 없으면 DB 쿼리로 fallback"""
        # TestRegistration 생성
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        # is_registered_flag를 설정하지 않음
        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        # DB 쿼리를 통해 확인
        self.assertTrue(serializer.data['is_registered'])

    def test_registration_count_zero(self):
        """성공: 등록자가 없을 때 registration_count=0"""
        # registration_count를 annotate로 설정
        self.test.registration_count = 0

        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        self.assertEqual(serializer.data['registration_count'], 0)

    def test_registration_count_multiple(self):
        """성공: 여러 명이 등록한 경우 올바른 registration_count"""
        # 여러 사용자 등록
        user2 = User.objects.create_user(
            email='user2@example.com',
            username='user2',
            password='testpass123'
        )
        user3 = User.objects.create_user(
            email='user3@example.com',
            username='user3',
            password='testpass123'
        )

        TestRegistration.objects.create(user=self.user, test=self.test)
        TestRegistration.objects.create(user=user2, test=self.test)
        TestRegistration.objects.create(user=user3, test=self.test)

        # registration_count를 annotate로 설정
        self.test.registration_count = 3

        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        self.assertEqual(serializer.data['registration_count'], 3)

    def test_price_format(self):
        """성공: price가 올바른 형식으로 직렬화"""
        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        # DecimalField는 문자열로 직렬화됨
        self.assertEqual(serializer.data['price'], '50000.00')

    def test_datetime_fields_format(self):
        """성공: datetime 필드들이 ISO 8601 형식으로 직렬화"""
        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            self.test,
            context={'request': request}
        )

        # datetime 필드들이 문자열로 직렬화되어야 함
        self.assertIsInstance(serializer.data['start_at'], str)
        self.assertIsInstance(serializer.data['end_at'], str)
        self.assertIsInstance(serializer.data['created_at'], str)

        # ISO 8601 형식 확인 (Z로 끝나는지)
        self.assertTrue(serializer.data['start_at'].endswith('Z'))
        self.assertTrue(serializer.data['end_at'].endswith('Z'))
        self.assertTrue(serializer.data['created_at'].endswith('Z'))

    def test_read_only_fields(self):
        """성공: 읽기 전용 필드는 업데이트 불가"""
        request = self.factory.get('/fake-path')
        request.user = self.user

        # 읽기 전용 필드를 변경하려고 시도
        data = {
            'id': 999,
            'created_at': timezone.now() + timedelta(days=100),
            'title': 'Updated Title',
        }

        serializer = TestSerializer(
            self.test,
            data=data,
            partial=True,
            context={'request': request}
        )

        self.assertTrue(serializer.is_valid())
        # id와 created_at는 변경되지 않아야 함
        self.assertNotEqual(self.test.id, 999)

    def test_serializer_with_null_description(self):
        """성공: description이 null인 경우"""
        test = Test.objects.create(
            title='Test without description',
            description=None,
            price=Decimal('30000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=7)
        )

        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            test,
            context={'request': request}
        )

        self.assertIsNone(serializer.data['description'])

    def test_multiple_tests_serialization(self):
        """성공: 여러 Test 객체를 한 번에 직렬화"""
        test2 = Test.objects.create(
            title='Python Test',
            description='Python basics',
            price=Decimal('45000.00'),
            start_at=self.now,
            end_at=self.now + timedelta(days=30)
        )

        # 첫 번째 시험에만 등록
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        tests = [self.test, test2]

        # Annotate 설정
        self.test.registration_count = 1
        self.test.is_registered_flag = True
        test2.registration_count = 0
        test2.is_registered_flag = False

        request = self.factory.get('/fake-path')
        request.user = self.user

        serializer = TestSerializer(
            tests,
            many=True,
            context={'request': request}
        )

        data = serializer.data
        self.assertEqual(len(data), 2)
        self.assertTrue(data[0]['is_registered'])
        self.assertFalse(data[1]['is_registered'])

    def test_different_user_sees_different_is_registered(self):
        """성공: 다른 사용자는 다른 is_registered 값을 봄"""
        # user만 등록
        TestRegistration.objects.create(
            user=self.user,
            test=self.test
        )

        # user의 경우
        request1 = self.factory.get('/fake-path')
        request1.user = self.user
        serializer1 = TestSerializer(
            self.test,
            context={'request': request1}
        )

        # other_user의 경우
        request2 = self.factory.get('/fake-path')
        request2.user = self.other_user
        serializer2 = TestSerializer(
            self.test,
            context={'request': request2}
        )

        self.assertTrue(serializer1.data['is_registered'])
        self.assertFalse(serializer2.data['is_registered'])
