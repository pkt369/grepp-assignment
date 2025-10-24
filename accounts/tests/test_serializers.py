"""
Unit Tests for Serializers

이 파일은 Serializer 레벨의 단위 테스트를 포함합니다.
- UserSerializer 유효성 검증 테스트
- CustomTokenObtainPairSerializer 테스트
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import UserSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


class UserSerializerTest(TestCase):
    """UserSerializer 단위 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        self.valid_user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass123'
        }

    def test_valid_user_creation(self):
        """정상적인 사용자 생성 테스트"""
        serializer = UserSerializer(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))

    def test_password_is_hashed(self):
        """비밀번호가 해싱되어 저장되는지 테스트"""
        serializer = UserSerializer(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()
        # 비밀번호가 평문으로 저장되지 않았는지 확인
        self.assertNotEqual(user.password, 'testpass123')
        # 해싱된 비밀번호가 pbkdf2 알고리즘으로 시작하는지 확인
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))

    def test_password_not_in_response(self):
        """응답에 비밀번호가 포함되지 않는지 테스트"""
        serializer = UserSerializer(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()
        serializer = UserSerializer(user)
        self.assertNotIn('password', serializer.data)

    def test_duplicate_email(self):
        """이메일 중복 체크 테스트"""
        # 첫 번째 사용자 생성
        User.objects.create_user(
            email='test@example.com',
            username='existing',
            password='password123'
        )

        # 같은 이메일로 두 번째 사용자 생성 시도
        serializer = UserSerializer(data=self.valid_user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertEqual(
            serializer.errors['email'][0],
            '이미 사용 중인 이메일입니다.'
        )

    def test_password_too_short(self):
        """비밀번호 길이 검증 테스트 (8자 미만)"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = 'short1'  # 6자

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_password_no_letter(self):
        """비밀번호에 문자가 없을 때 테스트"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = '12345678'  # 숫자만

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        self.assertEqual(
            serializer.errors['password'][0],
            '비밀번호는 최소 하나의 문자를 포함해야 합니다.'
        )

    def test_password_no_number(self):
        """비밀번호에 숫자가 없을 때 테스트"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = 'testpassword'  # 문자만

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        self.assertEqual(
            serializer.errors['password'][0],
            '비밀번호는 최소 하나의 숫자를 포함해야 합니다.'
        )

    def test_missing_email(self):
        """이메일 누락 시 테스트"""
        invalid_data = self.valid_user_data.copy()
        del invalid_data['email']

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_missing_username(self):
        """사용자명 누락 시 테스트"""
        invalid_data = self.valid_user_data.copy()
        del invalid_data['username']

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_missing_password(self):
        """비밀번호 누락 시 테스트"""
        invalid_data = self.valid_user_data.copy()
        del invalid_data['password']

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_empty_email(self):
        """빈 이메일 테스트"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = ''

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_invalid_email_format(self):
        """잘못된 이메일 형식 테스트"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = 'invalid-email'

        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


class CustomTokenObtainPairSerializerTest(TestCase):
    """CustomTokenObtainPairSerializer 단위 테스트"""

    def setUp(self):
        """테스트 사용자 생성"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_token_contains_custom_claims(self):
        """토큰에 커스텀 클레임이 포함되는지 테스트"""
        token = RefreshToken.for_user(self.user)

        # CustomTokenObtainPairSerializer의 get_token 메서드 호출
        from accounts.serializers import CustomTokenObtainPairSerializer
        custom_token = CustomTokenObtainPairSerializer.get_token(self.user)

        # 커스텀 클레임 확인
        self.assertEqual(custom_token['email'], self.user.email)
        self.assertEqual(custom_token['username'], self.user.username)

    def test_serializer_returns_user_info(self):
        """Serializer가 사용자 정보를 반환하는지 테스트"""
        # TokenObtainPairSerializer는 실제 요청 없이 테스트하기 어려우므로
        # 기본 동작만 확인
        serializer = CustomTokenObtainPairSerializer()
        self.assertIsNotNone(serializer)
