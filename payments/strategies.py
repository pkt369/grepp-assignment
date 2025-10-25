"""
결제 전략 패턴 (Strategy Pattern) 구현

각 결제 수단별로 다른 처리 로직을 캡슐화하여 유연하게 확장 가능하도록 구현
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import Payment


class PaymentStrategy(ABC):
    """결제 전략 추상 클래스"""

    @abstractmethod
    def get_payment_method(self) -> str:
        """결제 수단 반환"""
        pass

    @abstractmethod
    def validate_payment(self, amount: Decimal, **kwargs) -> tuple[bool, Optional[str]]:
        """
        결제 검증

        Returns:
            (is_valid, error_message): 검증 성공 여부와 에러 메시지
        """
        pass

    @abstractmethod
    def process_payment(
        self,
        user,
        amount: Decimal,
        payment_type: str,
        target_model,
        target_id: int,
        **kwargs
    ) -> Payment:
        """
        결제 처리

        Returns:
            Payment: 생성된 결제 객체
        """
        pass

    def get_transaction_metadata(self, **kwargs) -> Dict[str, Any]:
        """
        거래 메타데이터 반환 (선택적 구현)

        Returns:
            Dict: 거래 관련 추가 정보
        """
        return {}


class KakaoPayStrategy(PaymentStrategy):
    """카카오페이 결제 전략"""

    def get_payment_method(self) -> str:
        return 'kakaopay'

    def validate_payment(self, amount: Decimal, **kwargs) -> tuple[bool, Optional[str]]:
        """카카오페이 결제 검증"""
        # 카카오페이 특화 검증 로직
        if amount < Decimal('100'):
            return False, "카카오페이는 최소 100원 이상 결제 가능합니다"

        if amount > Decimal('50000000'):  # 5천만원
            return False, "카카오페이는 5천만원 이하만 결제 가능합니다"

        return True, None

    def process_payment(
        self,
        user,
        amount: Decimal,
        payment_type: str,
        target_model,
        target_id: int,
        **kwargs
    ) -> Payment:
        """카카오페이 결제 처리"""
        with transaction.atomic():
            payment = Payment.objects.create(
                user=user,
                payment_type=payment_type,
                content_type=ContentType.objects.get_for_model(target_model),
                object_id=target_id,
                amount=amount,
                payment_method=self.get_payment_method(),
                status='paid',
                external_transaction_id=kwargs.get('external_transaction_id', f'KAKAO_{user.id}_{target_id}')
            )

            # 카카오페이 API 호출 로직 (실제로는 외부 API 호출)
            # self._call_kakaopay_api(payment)

            return payment

    def get_transaction_metadata(self, **kwargs) -> Dict[str, Any]:
        """카카오페이 거래 메타데이터"""
        return {
            'payment_gateway': 'kakaopay',
            'supports_refund': True,
            'processing_fee_rate': 0.029,  # 2.9%
            'estimated_fee': kwargs.get('amount', 0) * Decimal('0.029')
        }


class CardPaymentStrategy(PaymentStrategy):
    """카드 결제 전략"""

    def get_payment_method(self) -> str:
        return 'card'

    def validate_payment(self, amount: Decimal, **kwargs) -> tuple[bool, Optional[str]]:
        """카드 결제 검증"""
        # 카드 결제 특화 검증 로직
        if amount < Decimal('1000'):
            return False, "카드 결제는 최소 1,000원 이상 가능합니다"

        if amount > Decimal('100000000'):  # 1억
            return False, "카드 결제는 1억원 이하만 가능합니다"

        return True, None

    def process_payment(
        self,
        user,
        amount: Decimal,
        payment_type: str,
        target_model,
        target_id: int,
        **kwargs
    ) -> Payment:
        """카드 결제 처리"""
        with transaction.atomic():
            payment = Payment.objects.create(
                user=user,
                payment_type=payment_type,
                content_type=ContentType.objects.get_for_model(target_model),
                object_id=target_id,
                amount=amount,
                payment_method=self.get_payment_method(),
                status='paid',
                external_transaction_id=kwargs.get('external_transaction_id', f'CARD_{user.id}_{target_id}')
            )

            # PG사 카드 결제 API 호출 로직
            # self._call_pg_card_api(payment)

            return payment

    def get_transaction_metadata(self, **kwargs) -> Dict[str, Any]:
        """카드 거래 메타데이터"""
        return {
            'payment_gateway': 'card_pg',
            'supports_refund': True,
            'supports_installment': True,
            'processing_fee_rate': 0.032,  # 3.2%
            'estimated_fee': kwargs.get('amount', 0) * Decimal('0.032')
        }


class BankTransferStrategy(PaymentStrategy):
    """계좌이체 결제 전략"""

    def get_payment_method(self) -> str:
        return 'bank_transfer'

    def validate_payment(self, amount: Decimal, **kwargs) -> tuple[bool, Optional[str]]:
        """계좌이체 결제 검증"""
        # 계좌이체 특화 검증 로직
        if amount < Decimal('1000'):
            return False, "계좌이체는 최소 1,000원 이상 가능합니다"

        if amount > Decimal('200000000'):  # 2억
            return False, "계좌이체는 2억원 이하만 가능합니다"

        return True, None

    def process_payment(
        self,
        user,
        amount: Decimal,
        payment_type: str,
        target_model,
        target_id: int,
        **kwargs
    ) -> Payment:
        """계좌이체 결제 처리"""
        with transaction.atomic():
            payment = Payment.objects.create(
                user=user,
                payment_type=payment_type,
                content_type=ContentType.objects.get_for_model(target_model),
                object_id=target_id,
                amount=amount,
                payment_method=self.get_payment_method(),
                status='paid',
                external_transaction_id=kwargs.get('external_transaction_id', f'BANK_{user.id}_{target_id}')
            )

            # 은행 API 호출 로직
            # self._call_bank_transfer_api(payment)

            return payment

    def get_transaction_metadata(self, **kwargs) -> Dict[str, Any]:
        """계좌이체 거래 메타데이터"""
        return {
            'payment_gateway': 'bank_transfer',
            'supports_refund': True,
            'processing_fee_rate': 0.005,  # 0.5% (낮은 수수료)
            'estimated_fee': kwargs.get('amount', 0) * Decimal('0.005')
        }


class PaymentStrategyFactory:
    """결제 전략 팩토리"""

    _strategies = {
        'kakaopay': KakaoPayStrategy,
        'card': CardPaymentStrategy,
        'bank_transfer': BankTransferStrategy,
    }

    @classmethod
    def get_strategy(cls, payment_method: str) -> PaymentStrategy:
        """
        결제 수단에 맞는 전략 반환

        Args:
            payment_method: 결제 수단 (kakaopay, card, bank_transfer)

        Returns:
            PaymentStrategy: 결제 전략 인스턴스

        Raises:
            ValueError: 지원하지 않는 결제 수단
        """
        strategy_class = cls._strategies.get(payment_method)
        if not strategy_class:
            raise ValueError(f"지원하지 않는 결제 수단입니다: {payment_method}")

        return strategy_class()

    @classmethod
    def get_supported_methods(cls) -> list[str]:
        """지원하는 결제 수단 목록 반환"""
        return list(cls._strategies.keys())

    @classmethod
    def register_strategy(cls, payment_method: str, strategy_class: type[PaymentStrategy]):
        """
        새로운 결제 전략 등록 (확장 가능)

        Args:
            payment_method: 결제 수단 이름
            strategy_class: 결제 전략 클래스
        """
        cls._strategies[payment_method] = strategy_class
