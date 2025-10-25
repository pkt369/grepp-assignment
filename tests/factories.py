import factory
from factory.django import DjangoModelFactory
from factory import SubFactory, Sequence, LazyAttribute, LazyFunction
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from accounts.models import User
from tests.models import Test, TestRegistration
from payments.models import Payment


class UserFactory(DjangoModelFactory):
    """User Factory"""

    class Meta:
        model = User

    email = Sequence(lambda n: f'user{n}@example.com')
    username = Sequence(lambda n: f'user{n}')
    password = factory.PostGenerationMethodCall('set_password', 'password123')


class TestFactory(DjangoModelFactory):
    """Test Factory"""

    class Meta:
        model = Test

    title = Sequence(lambda n: f'Test {n}')
    description = 'Test description'
    price = Decimal('45000.00')
    start_at = LazyFunction(lambda: timezone.now() - timedelta(days=365))
    end_at = LazyFunction(lambda: timezone.now() + timedelta(days=365))
    search_vector = None


class TestRegistrationFactory(DjangoModelFactory):
    """TestRegistration Factory"""

    class Meta:
        model = TestRegistration

    user = SubFactory(UserFactory)
    test = SubFactory(TestFactory)
    status = 'applied'
    applied_at = LazyFunction(timezone.now)


class PaymentFactory(DjangoModelFactory):
    """Payment Factory"""

    class Meta:
        model = Payment

    user = SubFactory(UserFactory)
    payment_type = 'test'
    content_type = LazyAttribute(lambda o: ContentType.objects.get_for_model(Test))
    object_id = LazyAttribute(lambda o: TestFactory.create().id)
    amount = Decimal('45000.00')
    payment_method = 'card'
    status = 'paid'
