import time
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create seed users for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing users before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        start_time = time.time()

        self.stdout.write(self.style.WARNING('\n=== 사용자 생성 시작 ==='))

        # Clear existing users if requested
        if clear:
            self.stdout.write('기존 사용자 삭제 중...')
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ 기존 사용자 삭제 완료'))

        # Create users
        self.stdout.write(f'{count}명의 사용자 생성 중...')

        domains = ['gmail.com', 'naver.com', 'kakao.com', 'daum.net', 'outlook.com']
        users = []

        for i in range(1, count + 1):
            domain = domains[i % len(domains)]
            users.append(User(
                username=f'user{i}',
                email=f'user{i}@{domain}',
                password='pbkdf2_sha256$600000$test$test123'  # Pre-hashed password
            ))

        # Bulk create users
        User.objects.bulk_create(users)

        # Calculate elapsed time
        elapsed = time.time() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ 사용자 {count}명 생성 완료 (소요 시간: {elapsed:.2f}초)\n'
            )
        )
