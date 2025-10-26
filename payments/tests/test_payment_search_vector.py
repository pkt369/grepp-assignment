import pytest
from factories import UserFactory, TestFactory, CourseFactory, PaymentFactory
from payments.models import Payment


@pytest.mark.django_db
class TestPaymentSearchVector:
    """Payment search_vector Signal 테스트"""

    def test_signal_updates_search_vector_on_create(self):
        """Payment 생성 시 search_vector가 자동으로 업데이트됨"""
        # Given & When: Payment 생성
        user = UserFactory()
        test = TestFactory(title='Django Test')
        payment = PaymentFactory(
            user=user,
            payment_type='test',
            object_id=test.id
        )

        # Then: search_vector가 자동으로 설정됨
        payment.refresh_from_db()
        assert payment.search_vector is not None

    def test_signal_updates_search_vector_for_course(self):
        """Course Payment도 search_vector 업데이트"""
        # Given & When: Course Payment 생성
        user = UserFactory()
        course = CourseFactory(title='Python Course')
        payment = PaymentFactory(
            user=user,
            payment_type='course',
            object_id=course.id,
            for_course=True
        )

        # Then: search_vector가 설정됨
        payment.refresh_from_db()
        assert payment.search_vector is not None

    def test_signal_updates_on_payment_update(self):
        """Payment 업데이트 시에도 search_vector 재설정"""
        # Given: Payment 생성
        user = UserFactory()
        test = TestFactory()
        payment = PaymentFactory(
            user=user,
            payment_type='test',
            object_id=test.id,
            status='paid'
        )

        # When: Payment 상태 변경
        payment.status = 'cancelled'
        payment.save()

        # Then: search_vector가 재설정됨
        payment.refresh_from_db()
        assert payment.search_vector is not None
