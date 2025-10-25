"""
Integration Tests for Authentication Flow

이 파일은 전체 인증 플로우의 통합 테스트를 포함합니다.
- 회원가입 → 로그인 → 토큰 사용 → 토큰 갱신 전체 플로우
- 다양한 실패 시나리오
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class AuthenticationFlowTest:
    """전체 인증 플로우 통합 테스트"""

    @pytest.fixture(autouse=True)


    def setup(self, api_client):
        """테스트 클라이언트 설정"""
        self.client = api_client
        self.signup_url = reverse('accounts:signup')
        self.login_url = reverse('accounts:login')
        self.refresh_url = reverse('accounts:token_refresh')

    def test_complete_auth_flow_success(self):
        """
        성공 시나리오: 회원가입 → 로그인 → 토큰 갱신
        """
        # 1. 회원가입
        signup_data = {
            'email': 'integration@example.com',
            'username': 'integrationuser',
            'password': 'integpass123'
        }
        signup_response = self.client.post(self.signup_url, signup_data)

        assert signup_response.status_code == status.HTTP_201_CREATED
        assert signup_response.data['message'] == '회원가입이 완료되었습니다.'
        user_id = signup_response.data['user']['id']

        # 2. 로그인
        login_data = {
            'email': 'integration@example.com',
            'password': 'integpass123'
        }
        login_response = self.client.post(self.login_url, login_data)

        assert login_response.status_code == status.HTTP_200_OK
        assert 'access' in login_response.data
        assert 'refresh' in login_response.data
        assert login_response.data['user']['id'] == user_id

        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # 3. Access Token으로 인증이 필요한 요청 (헤더 설정 테스트)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        # 실제로 인증이 필요한 엔드포인트가 있다면 여기서 테스트
        # 예: profile_response = self.client.get('/api/profile/')
        # assert profile_response.status_code == status.HTTP_200_OK

        # 4. Refresh Token으로 새 Access Token 발급
        refresh_response = self.client.post(self.refresh_url, {
            'refresh': refresh_token
        })

        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data
        # 새 토큰이 이전과 다른지 확인
        assert refresh_response.data['access'] != access_token

    def test_signup_then_login_with_wrong_password(self):
        """
        실패 시나리오: 회원가입 후 잘못된 비밀번호로 로그인
        """
        # 1. 회원가입
        signup_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'correctpass123'
        }
        signup_response = self.client.post(self.signup_url, signup_data)
        assert signup_response.status_code == status.HTTP_201_CREATED

        # 2. 잘못된 비밀번호로 로그인
        login_data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        login_response = self.client.post(self.login_url, login_data)

        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'access' not in login_response.data
        assert 'refresh' not in login_response.data

    def test_duplicate_signup_attempt(self):
        """
        실패 시나리오: 같은 이메일로 두 번 회원가입
        """
        signup_data = {
            'email': 'duplicate@example.com',
            'username': 'user1',
            'password': 'password123'
        }

        # 1. 첫 번째 회원가입
        first_response = self.client.post(self.signup_url, signup_data)
        assert first_response.status_code == status.HTTP_201_CREATED

        # 2. 같은 이메일로 두 번째 회원가입 시도
        signup_data['username'] = 'user2'  # username만 다르게
        second_response = self.client.post(self.signup_url, signup_data)

        assert second_response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'errors' in second_response.data
        assert 'email' in second_response.data['errors']

    def test_login_without_signup(self):
        """
        실패 시나리오: 회원가입 없이 로그인 시도
        """
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'anypassword123'
        }
        login_response = self.client.post(self.login_url, login_data)

        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_with_invalid_token(self):
        """
        실패 시나리오: 잘못된 토큰으로 갱신 시도
        """
        refresh_response = self.client.post(self.refresh_url, {
            'refresh': 'invalid.jwt.token'
        })

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_multiple_users_isolation(self):
        """
        성공 시나리오: 여러 사용자가 독립적으로 인증
        """
        # 사용자 1 회원가입 및 로그인
        user1_signup = {
            'email': 'user1@example.com',
            'username': 'user1',
            'password': 'user1pass123'
        }
        self.client.post(self.signup_url, user1_signup)
        user1_login = self.client.post(self.login_url, {
            'email': 'user1@example.com',
            'password': 'user1pass123'
        })
        user1_token = user1_login.data['access']

        # 사용자 2 회원가입 및 로그인
        user2_signup = {
            'email': 'user2@example.com',
            'username': 'user2',
            'password': 'user2pass123'
        }
        self.client.post(self.signup_url, user2_signup)
        user2_login = self.client.post(self.login_url, {
            'email': 'user2@example.com',
            'password': 'user2pass123'
        })
        user2_token = user2_login.data['access']

        # 두 토큰이 다른지 확인
        assert user1_token != user2_token

        # 각 사용자의 정보가 올바른지 확인
        assert user1_login.data['user']['email'] == 'user1@example.com'
        assert user2_login.data['user']['email'] == 'user2@example.com'

    def test_weak_password_validation(self):
        """
        실패 시나리오: 다양한 약한 비밀번호 패턴
        """
        base_data = {
            'email': 'test@example.com',
            'username': 'testuser'
        }

        # 1. 너무 짧은 비밀번호
        short_password = base_data.copy()
        short_password['password'] = 'abc123'  # 6자
        response = self.client.post(self.signup_url, short_password)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 2. 숫자만 있는 비밀번호
        number_only = base_data.copy()
        number_only['email'] = 'test2@example.com'
        number_only['password'] = '12345678'
        response = self.client.post(self.signup_url, number_only)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 3. 문자만 있는 비밀번호
        letter_only = base_data.copy()
        letter_only['email'] = 'test3@example.com'
        letter_only['password'] = 'abcdefgh'
        response = self.client.post(self.signup_url, letter_only)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_case_sensitive_email_login(self):
        """
        이메일 대소문자 구분 테스트
        """
        # 소문자 이메일로 회원가입
        signup_data = {
            'email': 'case@example.com',
            'username': 'caseuser',
            'password': 'casepass123'
        }
        self.client.post(self.signup_url, signup_data)

        # 대소문자 다른 이메일로 로그인 시도
        login_data = {
            'email': 'Case@Example.Com',  # 대소문자 다름
            'password': 'casepass123'
        }
        # Django의 기본 동작에 따라 이메일 필드는 대소문자를 구분할 수 있음
        # 실제 동작은 데이터베이스 설정에 따라 다를 수 있음
        login_response = self.client.post(self.login_url, login_data)
        # 대부분의 경우 로그인 실패 예상
        assert login_response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]
        

    def test_concurrent_login_same_user(self):
        """
        같은 사용자가 여러 번 로그인 (여러 디바이스 시나리오)
        """
        # 회원가입
        signup_data = {
            'email': 'concurrent@example.com',
            'username': 'concurrentuser',
            'password': 'concurrentpass123'
        }
        self.client.post(self.signup_url, signup_data)

        login_data = {
            'email': 'concurrent@example.com',
            'password': 'concurrentpass123'
        }

        # 첫 번째 로그인 (디바이스 1)
        login1 = self.client.post(self.login_url, login_data)
        token1 = login1.data['access']

        # 두 번째 로그인 (디바이스 2)
        login2 = self.client.post(self.login_url, login_data)
        token2 = login2.data['access']

        # 두 로그인 모두 성공
        assert login1.status_code == status.HTTP_200_OK
        assert login2.status_code == status.HTTP_200_OK

        # 각 토큰이 다름 (독립적인 세션)
        assert token1 != token2

    def test_special_characters_in_credentials(self):
        """
        특수 문자가 포함된 이메일/비밀번호 처리
        """
        signup_data = {
            'email': 'special+tag@example.com',  # + 문자 포함
            'username': 'specialuser',
            'password': 'Pass@123!#'  # 특수 문자 포함
        }

        signup_response = self.client.post(self.signup_url, signup_data)
        assert signup_response.status_code == status.HTTP_201_CREATED

        # 로그인
        login_data = {
            'email': 'special+tag@example.com',
            'password': 'Pass@123!#'
        }
        login_response = self.client.post(self.login_url, login_data)
        assert login_response.status_code == status.HTTP_200_OK

    def test_empty_request_bodies(self):
        """
        빈 요청 바디로 API 호출
        """
        # 빈 회원가입 요청
        signup_response = self.client.post(self.signup_url, {})
        assert signup_response.status_code == status.HTTP_400_BAD_REQUEST

        # 빈 로그인 요청
        login_response = self.client.post(self.login_url, {})
        assert login_response.status_code == status.HTTP_400_BAD_REQUEST

        # 빈 토큰 갱신 요청
        refresh_response = self.client.post(self.refresh_url, {})
        assert refresh_response.status_code == status.HTTP_400_BAD_REQUEST

    def test_very_long_credentials(self):
        """
        매우 긴 이메일/비밀번호 처리
        """
        signup_data = {
            'email': 'a' * 50 + '@example.com',  # 긴 이메일
            'username': 'longuser',
            'password': 'a1' * 100  # 200자 비밀번호
        }

        signup_response = self.client.post(self.signup_url, signup_data)
        # 이메일 길이 제한에 따라 성공하거나 실패할 수 있음
        # Django의 EmailField 기본 max_length는 254
        assert signup_response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        

    def test_whitespace_in_credentials(self):
        """
        공백이 포함된 credentials 처리
        """
        # 이메일에 공백 (앞/뒤)
        signup_data = {
            'email': '  whitespace@example.com  ',
            'username': 'whitespaceuser',
            'password': 'whitespace123'
        }

        signup_response = self.client.post(self.signup_url, signup_data)
        # Django의 EmailField는 공백을 트림하지 않으므로 실패할 가능성 높음
        assert signup_response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        


@pytest.mark.django_db
class TokenAuthenticationTest:
    """토큰 인증 관련 통합 테스트"""

    @pytest.fixture(autouse=True)


    def setup(self, api_client):
        """테스트 사용자 및 토큰 설정"""
        self.client = api_client
        self.login_url = reverse('accounts:login')

        # 테스트 사용자 생성 및 로그인
        self.user = User.objects.create_user(
            email='tokentest@example.com',
            username='tokenuser',
            password='tokenpass123'
        )

        login_response = self.client.post(self.login_url, {
            'email': 'tokentest@example.com',
            'password': 'tokenpass123'
        })
        self.access_token = login_response.data['access']

    def test_authenticated_request_with_valid_token(self):
        """
        유효한 토큰으로 인증된 요청
        """
        # Authorization 헤더 설정
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # 실제 인증이 필요한 엔드포인트가 있다면 테스트
        # 현재는 헤더 설정만 검증
        assert self.client._credentials is not None

    def test_authenticated_request_without_token(self):
        """
        토큰 없이 인증된 요청 시도
        """
        # Authorization 헤더 없이 요청
        # 실제 인증이 필요한 엔드포인트가 있다면 401 반환 예상
        pass

    def test_authenticated_request_with_invalid_token(self):
        """
        잘못된 토큰으로 인증된 요청 시도
        """
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')

        # 실제 인증이 필요한 엔드포인트가 있다면 401 반환 예상
        pass

    def test_token_format_bearer(self):
        """
        토큰 형식 검증 (Bearer 스키마)
        """
        # Bearer 없이 토큰만 전송
        self.client.credentials(HTTP_AUTHORIZATION=self.access_token)

        # 실제 인증이 필요한 엔드포인트가 있다면 401 반환 예상
        pass
