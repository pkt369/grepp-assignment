# 시험 응시 및 수업 수강 신청 시스템 API

Django REST Framework를 사용한 대규모 시험 응시 및 수업 수강 신청 백엔드 API 시스템입니다.

<br>

## 프로젝트 개요

100 만 개 이상의 시험 및 수업 데이터를 효율적으로 처리하는 백엔드 시스템입니다.
사용자는 JWT 를 이용해 인증하고, 시험 응시 및 수업 수강을 신청할 수 있습니다.
또, 결제 또는 결제 취소를 통해 수업 또는 시험을 관리할 수 있어야 합니다.
이때 중복 결제가 되지 않도록 락을 걸고 결제를 진행합니다.

### 핵심 요구 사항
- 100만 개 이상의 대용량 데이터 처리 ( 응답 시간: 1초 이내 )
- JWT 기반 인증/인가
- 결제 시스템 ( transaction 스냅샷 구조 )
- 트랜잭션을 통한 데이터 무결성 보장
- 페이지네이션, 필터링, 정렬 기능
- Docker 기반 배포 ( docker compose 사용 )
- 중복 결제 방지 ( Redis Lock 사용 )

### 참고 사항
- 실제 결제 시스템의 2단계 구조( Pre-Order => Approve ) 를 고려했으나, 현재 과제 범위에서는 결제와 주문을 하나의 트랜잭션으로 단순화하여 구현하였습니다.
- .env 는 현업에서는 배포하지 않으나 과제를 쉽게 실행하기 위해 이번 프로젝트에서만 같이 배포합니다.
- 검색은 Postgresql 의 FTS 로 진행했으나, 더 빠른 속도를 위해 Elasitc Search 나 MeiliSerach 채택 가능.
- 지금은 1초 이내 검색이 되고 있어 캐싱을 진행하지 않았습니다. 

<br>


## 주요 기능

### 1. 인증 시스템
- 회원가입 (이메일 기반)
- JWT 토큰 로그인
- 토큰 기반 API 인증

### 2. 시험 관리
- 시험 목록 조회 (페이지네이션, 필터링, 정렬)
- 시험 응시 신청 (결제 포함)
- 시험 완료 처리
- 응시 가능 기간 검증

### 3. 수업 관리
- 수업 목록 조회 (페이지네이션, 필터링, 정렬)
- 수업 수강 신청 (결제 포함)
- 수강 완료 처리
- 수강 가능 기간 검증

### 4. 결제 시스템
- 결제 내역 조회
- 결제 취소 (완료 전 항목만)
- 결제 상태 관리 (paid/cancelled)
- 날짜 범위 필터링

### 5. 성능 최적화
- 데이터베이스 인덱싱
- 쿼리 최적화 ( select_related: join 사용, prefetch_related: 별도 쿼리와 메모리 사용 )
- 페이지네이션을 통한 대용량 데이터 처리
- N+1 쿼리 문제 해결

<br>

## 기술 스택

**Backend**: Python 3.13, Django 5.2.7, Django REST Framework 3.16.1, djangorestframework-simplejwt 5.5.1
**Database**: PostgreSQL 17
**DevOps**: Docker, Docker Compose, Git, GitHub, Redis: 7.2
**Libraries**: psycopg2-binary - Postgres 어댑터, django-filter - 필터링, drf-spectacular - API 문서 자동 생성, python-dotenv - 환경 변수 관리
**Testing**: pytest - 테스트 프레임 워크, pytest-django - Django 테스트 통합, factory-boy: 테스트 데이터 생성

<br>

## 실행 방법
```
https://github.com/pkt369/grepp-assignment.git
cd grepp-assignment

docker compose up -d --build
docker compose exec web python manage.py seed_all
```

> 참고 seed 데이터가 100만건을 넣는 부분이라 약 2분정도가 소요 됩니다. ( 컴퓨터 사양에 따라 달라질 수 있습니다. )

<br>

### 벤치마크 실행
docker 에서 seed 데이터 넣은 후 실행
```bash
# 벤치마크 테스트
docker compose exec web python manage.py benchmark --runs=5

# 실제 사용되는 쿼리 확인
docker compose exec web python manage.py explain_queries
```
위 명령어를 실행하면 파일이 생깁니다. 파일안에 실행한 명령어에 대한 내용이 적혀있습니다.

<br>

### 테스트

```bash
# 테스트 실행 
source venv/bin/activate && DB_HOST=localhost REDIS_HOST=localhost pytest
```

<br>

## API 문서

API 문서는 Swagger 통해 구현하였습니다.

서버 실행후 아래 링크에서 확인 가능합니다.

http://localhost:8000/api/docs 

혹 접근이 안되는 경우 오프라인으로 접근 가능합니다.

docs/API.md 파일 참고해주세요.

<br>


<details>
<summary>API</summary>

### 인증
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/signup/` | 회원가입 | X |
| POST | `/login/` | 로그인 (JWT 발급) | X |
| POST | `/token/refresh/` | JWT 토큰 갱신 | X |

### 시험
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/tests/` | 시험 목록 조회 | O |
| POST | `/tests/{id}/apply/` | 시험 응시 신청 | O |
| POST | `/tests/{id}/complete/` | 시험 완료 처리 | O |

### 수업
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/courses/` | 수업 목록 조회 | O |
| POST | `/courses/{id}/enroll/` | 수업 수강 신청 | O |
| POST | `/courses/{id}/complete/` | 수강 완료 처리 | O |

### 결제
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/me/payments/` | 결제 내역 조회 | O |
| POST | `/payments/{id}/cancel/` | 결제 취소 | O |

</details>

<br>

## 데이터베이스 설계

<details>
<summary>테이블 정보</summary>

### User (users)
| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 사용자 ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 이메일 |
| username | VARCHAR(150) | UNIQUE, NOT NULL | 사용자명 |
| password | VARCHAR(128) | NOT NULL | 해시된 비밀번호 |
| is_active | BOOLEAN | DEFAULT TRUE | 활성화 상태 (soft_delete) |
| last_login | TIMESTAMP | NULL | 마지막 로그인 |

### Test (tests)
| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 시험 ID |
| title | VARCHAR(255) | NOT NULL | 시험 제목 |
| description | TEXT | NULL | 시험 설명 |
| price | DECIMAL(10,2) | NOT NULL | 시험 가격 |
| start_at | TIMESTAMP | NOT NULL | 응시 시작일 |
| end_at | TIMESTAMP | NOT NULL | 응시 종료일 |
| created_at | TIMESTAMP | NOT NULL | 생성일 |
| updated_at | TIMESTAMP | NOT NULL | 수정일 |

**인덱스:**
- `idx_test_dates` ON (start_at, end_at)
- `idx_test_created` ON (created_at DESC)
- `idx_test_composite` ON (start_at, end_at, created_at DESC)

### Course (courses)
| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 수업 ID |
| title | VARCHAR(255) | NOT NULL | 수업 제목 |
| description | TEXT | NULL | 수업 설명 |
| price | DECIMAL(10,2) | NOT NULL | 수업 가격 |
| start_at | TIMESTAMP | NOT NULL | 수강 시작일 |
| end_at | TIMESTAMP | NOT NULL | 수강 종료일 |
| created_at | TIMESTAMP | NOT NULL | 생성일 |
| updated_at | TIMESTAMP | NOT NULL | 수정일 |

**인덱스:**
- `idx_course_dates` ON (start_at, end_at)
- `idx_course_created` ON (created_at DESC)
- `idx_course_composite` ON (start_at, end_at, created_at DESC)

### TestRegistration (test_registrations)
| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 응시 등록 ID |
| user_id | INTEGER | FK(users.id), NOT NULL | 사용자 ID |
| test_id | INTEGER | FK(tests.id), NOT NULL | 시험 ID |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'applied' | 상태 (applied/completed/cancelled) |
| applied_at | TIMESTAMP | NOT NULL | 신청일시 |
| completed_at | TIMESTAMP | NULL | 완료일시 |
| cancelled_at | TIMESTAMP | NULL | 취소일시 |

**제약조건:**
- UNIQUE(user_id, test_id) - 중복 응시 방지

**인덱스:**
- `idx_test_reg_unique` ON (user_id, test_id) UNIQUE
- `idx_test_reg_status` ON (status)
- `idx_test_reg_user` ON (user_id)

### CourseRegistration (course_registrations)
| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 수강 등록 ID |
| user_id | INTEGER | FK(users.id), NOT NULL | 사용자 ID |
| course_id | INTEGER | FK(courses.id), NOT NULL | 수업 ID |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'enrolled' | 상태 (enrolled/completed/cancelled) |
| enrolled_at | TIMESTAMP | NOT NULL | 신청일시 |
| completed_at | TIMESTAMP | NULL | 완료일시 |
| cancelled_at | TIMESTAMP | NULL | 취소일시 |

**제약조건:**
- UNIQUE(user_id, course_id) - 중복 수강 방지

**인덱스:**
- `idx_course_reg_unique` ON (user_id, course_id) UNIQUE
- `idx_course_reg_status` ON (status)
- `idx_course_reg_user` ON (user_id)

### Payment (payments)
| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 결제 ID |
| user_id | INTEGER | FK(users.id), NOT NULL | 사용자 ID |
| payment_type | VARCHAR(20) | NOT NULL | 결제 대상 (test/course) |
| content_type_id | INTEGER | FK(content_type.id), NOT NULL | ContentType ID |
| object_id | INTEGER | NOT NULL | 대상 ID (test_id or course_id) |
| amount | DECIMAL(10,2) | NOT NULL | 결제 금액 |
| payment_method | VARCHAR(50) | NOT NULL | 결제 수단 (kakaopay/card/bank_transfer) |
| external_transaction_id | VARCHAR(100) | NULL | PG사 거래 식별자 (예: 결제사 응답값) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'paid' | 결제 상태 (paid/cancelled) |
| refund_reason | TEXT | NULL | 환불 시 사유 |
| paid_at | TIMESTAMP | NOT NULL | 결제일시 |
| cancelled_at | TIMESTAMP | NULL | 취소일시 |


**인덱스:**
- `idx_payment_user_status` ON (user_id, status)
- `idx_payment_paid_at` ON (paid_at)
- `idx_payment_status_date` ON (status, paid_at)

<br>

### 관계 (Relationships)

| 테이블 A | 관계 | 테이블 B | 설명 |
|---------|------|---------|------|
| User | 1:N | TestRegistration | 한 사용자는 여러 시험 응시 가능 |
| Test | 1:N | TestRegistration | 한 시험에 여러 사용자 응시 가능 |
| User | 1:N | CourseRegistration | 한 사용자는 여러 수업 수강 가능 |
| Course | 1:N | CourseRegistration | 한 수업에 여러 사용자 수강 가능 |
| User | 1:N | Payment | 한 사용자는 여러 결제 가능 |
| Payment | N:1 | Test or Course | 결제는 시험 또는 수업과 연결 (GenericForeignKey) |

</details>

<br>

### ERD

<img width="1108" height="1177" alt="Image" src="https://github.com/user-attachments/assets/f8abf49d-a871-4afe-a6dd-3b56f711ddc1" />

<br>














