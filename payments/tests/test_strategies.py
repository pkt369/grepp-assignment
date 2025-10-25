import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from payments.strategies import (
    PaymentStrategy,
    KakaoPayStrategy,
    CardPaymentStrategy,
    BankTransferStrategy,
    PaymentStrategyFactory
)
from payments.models import Payment
from tests.models import Test
from tests.factories import UserFactory, TestFactory

User = get_user_model()


@pytest.mark.django_db
class TestPaymentStrategyFactory:
    """PaymentStrategyFactory 테스트"""

    def test_get_strategy_kakaopay(self):
        """카카오페이 전략 반환"""
        strategy = PaymentStrategyFactory.get_strategy('kakaopay')
        assert isinstance(strategy, KakaoPayStrategy)
        assert strategy.get_payment_method() == 'kakaopay'

    def test_get_strategy_card(self):
        """카드 전략 반환"""
        strategy = PaymentStrategyFactory.get_strategy('card')
        assert isinstance(strategy, CardPaymentStrategy)
        assert strategy.get_payment_method() == 'card'

    def test_get_strategy_bank_transfer(self):
        """계좌이체 전략 반환"""
        strategy = PaymentStrategyFactory.get_strategy('bank_transfer')
        assert isinstance(strategy, BankTransferStrategy)
        assert strategy.get_payment_method() == 'bank_transfer'

    def test_get_strategy_invalid_method(self):
        """지원하지 않는 결제 수단"""
        with pytest.raises(ValueError) as exc_info:
            PaymentStrategyFactory.get_strategy('invalid_method')
        assert "지원하지 않는 결제 수단입니다" in str(exc_info.value)

    def test_get_supported_methods(self):
        """지원하는 결제 수단 목록"""
        methods = PaymentStrategyFactory.get_supported_methods()
        assert 'kakaopay' in methods
        assert 'card' in methods
        assert 'bank_transfer' in methods
        assert len(methods) == 3


@pytest.mark.django_db
class TestKakaoPayStrategy:
    """KakaoPayStrategy 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행"""
        self.strategy = KakaoPayStrategy()
        self.user = UserFactory()
        self.test = TestFactory(price=Decimal('45000.00'))

    def test_validate_payment_success(self):
        """정상 금액 검증 성공"""
        is_valid, error = self.strategy.validate_payment(Decimal('45000.00'))
        assert is_valid is True
        assert error is None

    def test_validate_payment_too_small(self):
        """최소 금액 미만"""
        is_valid, error = self.strategy.validate_payment(Decimal('50.00'))
        assert is_valid is False
        assert "최소 100원 이상" in error

    def test_validate_payment_too_large(self):
        """최대 금액 초과"""
        is_valid, error = self.strategy.validate_payment(Decimal('60000000.00'))
        assert is_valid is False
        assert "5천만원 이하" in error

    def test_process_payment(self):
        """결제 처리"""
        payment = self.strategy.process_payment(
            user=self.user,
            amount=Decimal('45000.00'),
            payment_type='test',
            target_model=Test,
            target_id=self.test.id
        )

        assert payment.user == self.user
        assert payment.amount == Decimal('45000.00')
        assert payment.payment_method == 'kakaopay'
        assert payment.status == 'paid'
        assert payment.payment_type == 'test'
        assert payment.object_id == self.test.id

    def test_get_transaction_metadata(self):
        """거래 메타데이터"""
        metadata = self.strategy.get_transaction_metadata(amount=Decimal('45000.00'))
        assert metadata['payment_gateway'] == 'kakaopay'
        assert metadata['supports_refund'] is True
        assert metadata['processing_fee_rate'] == 0.029
        assert metadata['estimated_fee'] == Decimal('45000.00') * Decimal('0.029')


@pytest.mark.django_db
class TestCardPaymentStrategy:
    """CardPaymentStrategy 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행"""
        self.strategy = CardPaymentStrategy()
        self.user = UserFactory()
        self.test = TestFactory(price=Decimal('45000.00'))

    def test_validate_payment_success(self):
        """정상 금액 검증 성공"""
        is_valid, error = self.strategy.validate_payment(Decimal('45000.00'))
        assert is_valid is True
        assert error is None

    def test_validate_payment_too_small(self):
        """최소 금액 미만"""
        is_valid, error = self.strategy.validate_payment(Decimal('500.00'))
        assert is_valid is False
        assert "최소 1,000원" in error

    def test_validate_payment_too_large(self):
        """최대 금액 초과"""
        is_valid, error = self.strategy.validate_payment(Decimal('150000000.00'))
        assert is_valid is False
        assert "1억원 이하" in error

    def test_process_payment(self):
        """결제 처리"""
        payment = self.strategy.process_payment(
            user=self.user,
            amount=Decimal('45000.00'),
            payment_type='test',
            target_model=Test,
            target_id=self.test.id
        )

        assert payment.user == self.user
        assert payment.amount == Decimal('45000.00')
        assert payment.payment_method == 'card'
        assert payment.status == 'paid'

    def test_get_transaction_metadata(self):
        """거래 메타데이터"""
        metadata = self.strategy.get_transaction_metadata(amount=Decimal('45000.00'))
        assert metadata['payment_gateway'] == 'card_pg'
        assert metadata['supports_refund'] is True
        assert metadata['supports_installment'] is True
        assert metadata['processing_fee_rate'] == 0.032


@pytest.mark.django_db
class TestBankTransferStrategy:
    """BankTransferStrategy 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행"""
        self.strategy = BankTransferStrategy()
        self.user = UserFactory()
        self.test = TestFactory(price=Decimal('45000.00'))

    def test_validate_payment_success(self):
        """정상 금액 검증 성공"""
        is_valid, error = self.strategy.validate_payment(Decimal('45000.00'))
        assert is_valid is True
        assert error is None

    def test_validate_payment_too_small(self):
        """최소 금액 미만"""
        is_valid, error = self.strategy.validate_payment(Decimal('500.00'))
        assert is_valid is False
        assert "최소 1,000원" in error

    def test_validate_payment_too_large(self):
        """최대 금액 초과"""
        is_valid, error = self.strategy.validate_payment(Decimal('250000000.00'))
        assert is_valid is False
        assert "2억원 이하" in error

    def test_process_payment(self):
        """결제 처리"""
        payment = self.strategy.process_payment(
            user=self.user,
            amount=Decimal('45000.00'),
            payment_type='test',
            target_model=Test,
            target_id=self.test.id
        )

        assert payment.user == self.user
        assert payment.amount == Decimal('45000.00')
        assert payment.payment_method == 'bank_transfer'
        assert payment.status == 'paid'

    def test_get_transaction_metadata(self):
        """거래 메타데이터"""
        metadata = self.strategy.get_transaction_metadata(amount=Decimal('45000.00'))
        assert metadata['payment_gateway'] == 'bank_transfer'
        assert metadata['supports_refund'] is True
        assert metadata['processing_fee_rate'] == 0.005  # 낮은 수수료


@pytest.mark.django_db
class TestPaymentStrategyExtension:
    """결제 전략 확장성 테스트"""

    def test_register_new_strategy(self):
        """새로운 결제 전략 등록"""
        # Custom Strategy 정의
        class CryptoPaymentStrategy(PaymentStrategy):
            def get_payment_method(self) -> str:
                return 'crypto'

            def validate_payment(self, amount: Decimal, **kwargs):
                return (True, None) if amount > 0 else (False, "Invalid amount")

            def process_payment(self, user, amount, payment_type, target_model, target_id, **kwargs):
                from django.contrib.contenttypes.models import ContentType
                return Payment.objects.create(
                    user=user,
                    payment_type=payment_type,
                    content_type=ContentType.objects.get_for_model(target_model),
                    object_id=target_id,
                    amount=amount,
                    payment_method=self.get_payment_method(),
                    status='paid'
                )

        # 새 전략 등록
        PaymentStrategyFactory.register_strategy('crypto', CryptoPaymentStrategy)

        # 등록된 전략 사용
        strategy = PaymentStrategyFactory.get_strategy('crypto')
        assert isinstance(strategy, CryptoPaymentStrategy)
        assert strategy.get_payment_method() == 'crypto'

        # 지원하는 결제 수단 목록에 포함됨
        methods = PaymentStrategyFactory.get_supported_methods()
        assert 'crypto' in methods
