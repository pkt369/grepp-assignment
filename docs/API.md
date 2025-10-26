# 시험 및 수업 관리 시스템 API 문서

## 1. 프로젝트 소개

### 시스템 개요
시험 응시 및 수업 수강 신청을 관리하는 REST API 시스템입니다. 사용자는 시험과 수업을 조회하고, 결제를 통해 응시/수강 신청을 할 수 있습니다.

### 주요 기능
- **인증 시스템**: JWT 토큰 기반 인증
- **시험 관리**: 시험 조회, 응시 신청, 완료 처리
- **수업 관리**: 수업 조회, 수강 신청, 완료 처리
- **결제 시스템**: 다양한 결제 수단 지원 (카카오페이, 카드, 계좌이체)
- **검색 기능**: PostgreSQL Full-Text Search 지원
- **동시성 제어**: Redis Lock을 활용한 중복 결제 방지

---

## 2. 인증

### JWT 토큰 기반 인증

이 API는 JWT (JSON Web Token) 기반 인증을 사용합니다.

#### 로그인 방법
1. `/api/auth/login/` 엔드포인트로 이메일과 비밀번호를 전송
2. 응답으로 `access` 토큰과 `refresh` 토큰을 받음
3. 이후 모든 API 요청 시 `Authorization` 헤더에 토큰 포함

#### Authorization 헤더 형식
```
Authorization: Bearer <access_token>
```

#### 토큰 갱신
- Access 토큰 만료 시: `/api/auth/token/refresh/` 엔드포인트 사용
- Refresh 토큰으로 새로운 Access 토큰 발급

---

## 3. API 엔드포인트 요약

### 인증 (Auth)
| HTTP 메서드 | URL | 설명 | 인증 필요 |
|------------|-----|------|----------|
| POST | `/api/auth/signup/` | 회원가입 | ❌ |
| POST | `/api/auth/login/` | 로그인 (JWT 토큰 발급) | ❌ |
| POST | `/api/auth/token/refresh/` | Access 토큰 갱신 | ❌ |

### 시험 (Tests)
| HTTP 메서드 | URL | 설명 | 인증 필요 |
|------------|-----|------|----------|
| GET | `/api/tests/` | 시험 목록 조회 | ✅ |
| GET | `/api/tests/{id}/` | 시험 상세 조회 | ✅ |
| POST | `/api/tests/{id}/apply/` | 시험 응시 신청 | ✅ |
| POST | `/api/tests/{id}/complete/` | 시험 완료 처리 | ✅ |

### 수업 (Courses)
| HTTP 메서드 | URL | 설명 | 인증 필요 |
|------------|-----|------|----------|
| GET | `/api/courses/` | 수업 목록 조회 | ✅ |
| GET | `/api/courses/{id}/` | 수업 상세 조회 | ✅ |
| POST | `/api/courses/{id}/enroll/` | 수업 수강 신청 | ✅ |
| POST | `/api/courses/{id}/complete/` | 수업 완료 처리 | ✅ |

### 결제 (Payments)
| HTTP 메서드 | URL | 설명 | 인증 필요 |
|------------|-----|------|----------|
| GET | `/api/me/payments/` | 본인 결제 내역 목록 조회 | ✅ |
| GET | `/api/me/payments/{id}/` | 본인 결제 내역 상세 조회 | ✅ |
| POST | `/api/payments/{id}/cancel/` | 결제 취소 | ✅ |

---

## 4. 주요 엔드포인트 상세 설명

### 4.1 회원가입

**POST** `/api/auth/signup/`

새로운 사용자 계정을 생성합니다.

**요청 바디:**
```json
{
  "email": "user@example.com",
  "username": "홍길동",
  "password": "password123"
}
```

**응답 (201 Created):**
```json
{
  "message": "회원가입이 완료되었습니다.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "홍길동"
  }
}
```

**에러 응답 (400 Bad Request):**
```json
{
  "message": "회원가입에 실패했습니다.",
  "errors": {
    "email": ["이미 사용 중인 이메일입니다."],
    "password": ["비밀번호는 최소 하나의 문자를 포함해야 합니다."]
  }
}
```

---

### 4.2 로그인

**POST** `/api/auth/login/`

이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.

**요청 바디:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답 (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "홍길동"
  }
}
```

**에러 응답 (401 Unauthorized):**
```json
{
  "detail": "No active account found with the given credentials"
}
```

---

### 4.3 시험 목록 조회

**GET** `/api/tests/`

시험 목록을 조회합니다. 필터링, 검색, 정렬을 지원합니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**쿼리 파라미터:**
- `status` (선택): 상태 필터 (예: `available` - 현재 응시 가능한 시험만)
- `search` (선택): Full-Text Search (제목 및 설명 검색)
- `sort` (선택): 정렬 방식 (`created`: 최신순, `popular`: 인기순)
- `page` (선택): 페이지 번호 (기본값: 1)

**요청 예시:**
```
GET /api/tests/?status=available&sort=popular&page=1
```

**응답 (200 OK):**
```json
{
  "count": 15,
  "next": "http://localhost:8000/api/tests/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Django 기초 시험",
      "description": "Django 프레임워크의 기본 개념을 다루는 시험입니다.",
      "price": "45000.00",
      "start_at": "2025-01-01T00:00:00Z",
      "end_at": "2025-12-31T23:59:59Z",
      "created_at": "2025-01-01T00:00:00Z",
      "is_registered": false,
      "registration_count": 120
    }
  ]
}
```

---

### 4.4 시험 응시 신청

**POST** `/api/tests/{id}/apply/`

시험 응시를 신청합니다. 결제 정보를 함께 제공해야 합니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**요청 바디:**
```json
{
  "amount": "45000.00",
  "payment_method": "card"
}
```

**파라미터 설명:**
- `amount`: 결제 금액 (시험 가격과 일치해야 함)
- `payment_method`: 결제 수단 (`kakaopay`, `card`, `bank_transfer`)

**응답 (201 Created):**
```json
{
  "message": "시험 응시 신청이 완료되었습니다",
  "payment_id": 1,
  "registration_id": 1,
  "payment_method": "card",
  "transaction_metadata": {}
}
```

**에러 응답:**

- **400 Bad Request** (중복 신청):
```json
{
  "error": "이미 응시 신청한 시험입니다"
}
```

- **400 Bad Request** (금액 불일치):
```json
{
  "error": "결제 금액이 시험 가격과 일치하지 않습니다"
}
```

- **409 Conflict** (동시 요청 충돌):
```json
{
  "error": "잠시 후 다시 시도해주세요"
}
```

---

### 4.5 시험 완료 처리

**POST** `/api/tests/{id}/complete/`

시험을 완료 처리합니다. 이미 응시 신청한 시험만 완료할 수 있습니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**응답 (200 OK):**
```json
{
  "message": "시험이 완료되었습니다",
  "registration_id": 1,
  "completed_at": "2025-10-25T12:34:56Z"
}
```

**에러 응답:**

- **404 Not Found**:
```json
{
  "error": "응시 신청 내역이 없습니다"
}
```

- **400 Bad Request**:
```json
{
  "error": "이미 완료된 시험입니다"
}
```

---

### 4.6 수업 목록 조회

**GET** `/api/courses/`

수업 목록을 조회합니다. 필터링, 검색, 정렬을 지원합니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**쿼리 파라미터:**
- `status` (선택): 상태 필터 (예: `available` - 현재 수강 가능한 수업만)
- `search` (선택): Full-Text Search (제목 및 설명 검색)
- `sort` (선택): 정렬 방식 (`created`: 최신순, `popular`: 인기순)
- `page` (선택): 페이지 번호 (기본값: 1)

**응답 (200 OK):**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Python 웹 개발 완성",
      "description": "Django를 활용한 웹 애플리케이션 개발 과정",
      "price": "120000.00",
      "start_at": "2025-02-01T00:00:00Z",
      "end_at": "2025-03-31T23:59:59Z",
      "created_at": "2025-01-15T00:00:00Z",
      "is_registered": true,
      "registration_count": 45
    }
  ]
}
```

---

### 4.7 수업 수강 신청

**POST** `/api/courses/{id}/enroll/`

수업 수강을 신청합니다. 결제 정보를 함께 제공해야 합니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**요청 바디:**
```json
{
  "amount": "120000.00",
  "payment_method": "kakaopay"
}
```

**응답 (201 Created):**
```json
{
  "message": "수업 수강 신청이 완료되었습니다",
  "payment_id": 2,
  "enrollment_id": 1,
  "payment_method": "kakaopay",
  "transaction_metadata": {}
}
```

**에러 응답:** (시험 응시 신청과 동일)

---

### 4.8 결제 내역 조회

**GET** `/api/me/payments/`

본인의 결제 내역 목록을 조회합니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**쿼리 파라미터:**
- `status` (선택): 결제 상태 필터 (`paid`, `cancelled`, `refunded`)
- `payment_type` (선택): 결제 유형 필터 (`test`, `course`)
- `from` (선택): 결제 시작 날짜 (YYYY-MM-DD)
- `to` (선택): 결제 종료 날짜 (YYYY-MM-DD)
- `search` (선택): Full-Text Search (항목 제목 검색)

**요청 예시:**
```
GET /api/me/payments/?status=paid&payment_type=test&from=2025-01-01&to=2025-12-31
```

**응답 (200 OK):**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "payment_type": "test",
      "target_title": "Django 기초 시험",
      "target_type": "test",
      "target_id": 1,
      "amount": "45000.00",
      "payment_method": "card",
      "status": "paid",
      "paid_at": "2025-10-20T10:30:00Z",
      "cancelled_at": null,
      "registration_time": "2025-10-20T10:30:05Z"
    }
  ]
}
```

---

### 4.9 결제 취소

**POST** `/api/payments/{id}/cancel/`

결제를 취소합니다. 본인의 결제만 취소할 수 있으며, 관련 응시/수강 신청도 함께 취소됩니다.

**헤더:**
```
Authorization: Bearer <access_token>
```

**응답 (200 OK):**
```json
{
  "message": "결제가 취소되었습니다",
  "payment_id": 1,
  "cancelled_at": "2025-10-26T12:34:56Z"
}
```

**에러 응답:**

- **403 Forbidden**:
```json
{
  "error": "본인의 결제만 취소할 수 있습니다"
}
```

- **400 Bad Request**:
```json
{
  "error": "이미 취소된 결제입니다"
}
```

- **409 Conflict**:
```json
{
  "error": "잠시 후 다시 시도해주세요"
}
```

---

## 5. 사용 예시

### 5.1 cURL 예시

#### 회원가입
```bash
curl -X POST http://localhost:8000/api/auth/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "홍길동",
    "password": "password123"
  }'
```

#### 로그인
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

#### 시험 목록 조회 (JWT 토큰 사용)
```bash
curl -X GET "http://localhost:8000/api/tests/?status=available" \
  -H "Authorization: Bearer <access_token>"
```

#### 시험 응시 신청
```bash
curl -X POST http://localhost:8000/api/tests/1/apply/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "45000.00",
    "payment_method": "card"
  }'
```

#### 결제 취소
```bash
curl -X POST http://localhost:8000/api/payments/1/cancel/ \
  -H "Authorization: Bearer <access_token>"
```

---

### 5.2 Python requests 예시

```python
import requests

# 기본 URL
BASE_URL = "http://localhost:8000"

# 1. 회원가입
signup_response = requests.post(
    f"{BASE_URL}/api/auth/signup/",
    json={
        "email": "user@example.com",
        "username": "홍길동",
        "password": "password123"
    }
)
print(signup_response.json())

# 2. 로그인
login_response = requests.post(
    f"{BASE_URL}/api/auth/login/",
    json={
        "email": "user@example.com",
        "password": "password123"
    }
)
tokens = login_response.json()
access_token = tokens["access"]

# 3. 헤더 설정
headers = {
    "Authorization": f"Bearer {access_token}"
}

# 4. 시험 목록 조회
tests_response = requests.get(
    f"{BASE_URL}/api/tests/",
    headers=headers,
    params={"status": "available", "sort": "popular"}
)
print(tests_response.json())

# 5. 시험 응시 신청
apply_response = requests.post(
    f"{BASE_URL}/api/tests/1/apply/",
    headers=headers,
    json={
        "amount": "45000.00",
        "payment_method": "card"
    }
)
print(apply_response.json())

# 6. 결제 내역 조회
payments_response = requests.get(
    f"{BASE_URL}/api/me/payments/",
    headers=headers,
    params={"status": "paid"}
)
print(payments_response.json())

# 7. 결제 취소
cancel_response = requests.post(
    f"{BASE_URL}/api/payments/1/cancel/",
    headers=headers
)
print(cancel_response.json())
```

---

## 6. 에러 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 OK | 요청 성공 |
| 201 Created | 리소스 생성 성공 |
| 400 Bad Request | 잘못된 요청 (유효성 검증 실패, 중복 신청 등) |
| 401 Unauthorized | 인증 필요 (토큰 없음 또는 만료) |
| 403 Forbidden | 권한 없음 (본인의 데이터가 아님) |
| 404 Not Found | 리소스를 찾을 수 없음 |
| 409 Conflict | 동시 요청 충돌 (Redis Lock 실패) |
| 500 Internal Server Error | 서버 내부 오류 |

---

## 7. 제한사항 및 주의사항

### 페이지네이션
- 페이지당 **20개** 항목 반환
- `page` 파라미터로 페이지 지정 가능

### Redis Lock 타임아웃
- 결제 및 취소 작업 시 **10초** 타임아웃
- 동시 요청 시 409 Conflict 응답

### 접근 제어
- 결제 내역: **본인 데이터만** 조회 가능
- 결제 취소: **본인 결제만** 취소 가능

### 비즈니스 로직
- 시험/수업 **중복 신청 불가**
- 결제 금액과 시험/수업 가격 **일치 필수**
- 이미 완료되거나 취소된 시험/수업 **재완료 불가**

### JWT 토큰 유효기간
- **Access Token**: 24시간
- **Refresh Token**: 7일

---

## 8. Swagger UI 사용 방법

### 접속
브라우저에서 다음 URL로 접속:
```
http://localhost:8000/api/docs/
```

### 인증 설정
1. Swagger UI 우측 상단의 **Authorize** 버튼 클릭
2. `/api/auth/login/` 엔드포인트 호출하여 `access` 토큰 획득
3. 다음 형식으로 입력: `Bearer <access_token>`
4. **Authorize** 클릭
5. 이후 모든 요청에 자동으로 토큰 포함됨

### API 테스트
1. 원하는 엔드포인트 선택
2. **Try it out** 버튼 클릭
3. 필요한 파라미터 또는 요청 바디 입력
4. **Execute** 버튼 클릭
5. 하단에서 응답 확인

---

## 9. ReDoc 문서

더 깔끔한 문서 인터페이스를 원하시면 ReDoc을 사용하세요:
```
http://localhost:8000/api/redoc/
```

---

## 10. OpenAPI 스키마

OpenAPI 스키마 파일을 직접 다운로드하려면:
```
http://localhost:8000/api/schema/
```

또는 커맨드라인에서:
```bash
python manage.py spectacular --file schema.yml
```

