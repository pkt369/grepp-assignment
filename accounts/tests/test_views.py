"""
Unit Tests for Views

이 파일은 View 레벨의 단위 테스트를 포함합니다.
- SignupView 테스트
- LoginView 테스트
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


class SignupViewTest(TestCase):
    """SignupView 단위 테스트"""

    def setUp(self):
        """테스트 클라이언트 및 데이터 설정"""
        self.client = APIClient()
        self.signup_url = reverse('accounts:signup')
        self.valid_data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'newpass123'
        }

    def test_signup_success(self):
        """회원가입 성공 테스트"""
        response = self.client.post(self.signup_url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], '회원가입이 완료되었습니다.')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')
        self.assertEqual(response.data['user']['username'], 'newuser')
        self.assertNotIn('password', response.data['user'])

        # 데이터베이스에 사용자가 생성되었는지 확인
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_signup_duplicate_email(self):
        """중복 이메일로 회원가입 실패 테스트"""
        # 기존 사용자 생성
        User.objects.create_user(
            email='existing@example.com',
            username='existing',
            password='password123'
        )

        # 같은 이메일로 회원가입 시도
        duplicate_data = {
            'email': 'existing@example.com',
            'username': 'newuser',
            'password': 'newpass123'
        }
        response = self.client.post(self.signup_url, duplicate_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], '회원가입에 실패했습니다.')
        self.assertIn('errors', response.data)
        self.assertIn('email', response.data['errors'])

    def test_signup_missing_email(self):
        """이메일 누락 시 회원가입 실패 테스트"""
        invalid_data = self.valid_data.copy()
        del invalid_data['email']

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('email', response.data['errors'])

    def test_signup_missing_username(self):
        """사용자명 누락 시 회원가입 실패 테스트"""
        invalid_data = self.valid_data.copy()
        del invalid_data['username']

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('username', response.data['errors'])

    def test_signup_missing_password(self):
        """비밀번호 누락 시 회원가입 실패 테스트"""
        invalid_data = self.valid_data.copy()
        del invalid_data['password']

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('password', response.data['errors'])

    def test_signup_invalid_email(self):
        """잘못된 이메일 형식으로 회원가입 실패 테스트"""
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = 'invalid-email'

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('email', response.data['errors'])

    def test_signup_weak_password(self):
        """약한 비밀번호로 회원가입 실패 테스트 (숫자만)"""
        invalid_data = self.valid_data.copy()
        invalid_data['password'] = '12345678'

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('password', response.data['errors'])

    def test_signup_short_password(self):
        """짧은 비밀번호로 회원가입 실패 테스트"""
        invalid_data = self.valid_data.copy()
        invalid_data['password'] = 'short1'

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('password', response.data['errors'])

    def test_signup_empty_fields(self):
        """빈 필드로 회원가입 실패 테스트"""
        invalid_data = {
            'email': '',
            'username': '',
            'password': ''
        }

        response = self.client.post(self.signup_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)


class LoginViewTest(TestCase):
    """LoginView 단위 테스트"""

    def setUp(self):
        """테스트 사용자 및 클라이언트 설정"""
        self.client = APIClient()
        self.login_url = reverse('accounts:login')

        # 테스트 사용자 생성
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        self.valid_credentials = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

    def test_login_success(self):
        """로그인 성공 테스트"""
        response = self.client.post(self.login_url, self.valid_credentials)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertEqual(response.data['user']['username'], 'testuser')

    def test_login_wrong_password(self):
        """잘못된 비밀번호로 로그인 실패 테스트"""
        invalid_credentials = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post(self.login_url, invalid_credentials)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_login_wrong_email(self):
        """존재하지 않는 이메일로 로그인 실패 테스트"""
        invalid_credentials = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, invalid_credentials)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_email(self):
        """이메일 누락 시 로그인 실패 테스트"""
        invalid_credentials = {
            'password': 'testpass123'
        }

        response = self.client.post(self.login_url, invalid_credentials)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        """비밀번호 누락 시 로그인 실패 테스트"""
        invalid_credentials = {
            'email': 'test@example.com'
        }

        response = self.client.post(self.login_url, invalid_credentials)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_empty_credentials(self):
        """빈 credentials로 로그인 실패 테스트"""
        response = self.client.post(self.login_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        """비활성화된 사용자 로그인 실패 테스트"""
        # 사용자 비활성화
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.login_url, self.valid_credentials)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_structure(self):
        """발급된 토큰 구조 검증"""
        response = self.client.post(self.login_url, self.valid_credentials)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # access 토큰이 JWT 형식인지 확인 (3개 부분으로 나뉨)
        access_token = response.data['access']
        self.assertEqual(len(access_token.split('.')), 3)

        # refresh 토큰이 JWT 형식인지 확인
        refresh_token = response.data['refresh']
        self.assertEqual(len(refresh_token.split('.')), 3)


class TokenRefreshViewTest(TestCase):
    """TokenRefreshView 단위 테스트"""

    def setUp(self):
        """테스트 사용자 및 클라이언트 설정"""
        self.client = APIClient()
        self.login_url = reverse('accounts:login')
        self.refresh_url = reverse('accounts:token_refresh')

        # 테스트 사용자 생성 및 로그인
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        # 로그인하여 토큰 발급
        login_response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        self.refresh_token = login_response.data['refresh']
        self.access_token = login_response.data['access']

    def test_token_refresh_success(self):
        """토큰 갱신 성공 테스트"""
        response = self.client.post(self.refresh_url, {
            'refresh': self.refresh_token
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        # 새 access 토큰이 이전과 다른지 확인
        self.assertNotEqual(response.data['access'], self.access_token)

    def test_token_refresh_invalid_token(self):
        """잘못된 refresh 토큰으로 갱신 실패 테스트"""
        response = self.client.post(self.refresh_url, {
            'refresh': 'invalid.token.here'
        })

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_missing_token(self):
        """refresh 토큰 누락 시 실패 테스트"""
        response = self.client.post(self.refresh_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh_empty_token(self):
        """빈 refresh 토큰으로 갱신 실패 테스트"""
        response = self.client.post(self.refresh_url, {
            'refresh': ''
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
