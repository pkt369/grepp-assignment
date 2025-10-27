import time
import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class Command(BaseCommand):
    help = 'Run performance benchmarks on API endpoints'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='benchmark_results.json',
            help='Output file for benchmark results (JSON format)'
        )
        parser.add_argument(
            '--runs',
            type=int,
            default=5,
            help='Number of runs per endpoint (default: 5)'
        )

    @override_settings(DEBUG=True, ALLOWED_HOSTS=['*'])
    def handle(self, *args, **options):
        output_file = options['output']
        num_runs = options['runs']

        self.stdout.write(self.style.SUCCESS('Starting benchmark...'))

        # Create test user and get token
        user = self._get_or_create_test_user()
        token = self._get_token(user)

        # Initialize API client
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Define endpoints to test
        endpoints = [
            {'name': 'Test List', 'url': '/api/tests/', 'method': 'GET'},
            {'name': 'Test List (Search)', 'url': '/api/tests/?search=Django', 'method': 'GET'},
            {'name': 'Test List (Status Filter)', 'url': '/api/tests/?status=available', 'method': 'GET'},
            {'name': 'Test List (Popular Sort)', 'url': '/api/tests/?sort=popular', 'method': 'GET'},
            {'name': 'Test List (Complex)', 'url': '/api/tests/?search=Python&status=available&sort=created', 'method': 'GET'},
            {'name': 'Course List', 'url': '/api/courses/', 'method': 'GET'},
            {'name': 'Course List (Search)', 'url': '/api/courses/?search=Django', 'method': 'GET'},
            {'name': 'Course List (Status Filter)', 'url': '/api/courses/?status=available', 'method': 'GET'},
            {'name': 'Course List (Popular Sort)', 'url': '/api/courses/?sort=popular', 'method': 'GET'},
            {'name': 'Course List (Complex)', 'url': '/api/courses/?search=Django&sort=popular&status=available', 'method': 'GET'},
            {'name': 'Payment List', 'url': '/api/me/payments/', 'method': 'GET'},
            {'name': 'Payment List (Status Filter)', 'url': '/api/me/payments/?status=paid', 'method': 'GET'},
        ]

        results = []

        for endpoint in endpoints:
            self.stdout.write(f"\nTesting: {endpoint['name']}")

            endpoint_results = []

            for run in range(num_runs):
                # Reset query counter
                reset_queries()

                # Measure response time
                start_time = time.time()
                response = client.get(endpoint['url'])
                end_time = time.time()

                response_time = (end_time - start_time) * 1000  # Convert to ms
                query_count = len(connection.queries)

                endpoint_results.append({
                    'response_time': round(response_time, 2),
                    'query_count': query_count,
                    'status_code': response.status_code
                })

                self.stdout.write(
                    f"  Run {run + 1}: {response_time:.2f}ms, {query_count} queries"
                )

            # Calculate statistics
            response_times = [r['response_time'] for r in endpoint_results]
            query_counts = [r['query_count'] for r in endpoint_results]

            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            avg_query_count = sum(query_counts) / len(query_counts)

            result = {
                'endpoint': endpoint['name'],
                'url': endpoint['url'],
                'avg_response_time_ms': round(avg_response_time, 2),
                'min_response_time_ms': round(min_response_time, 2),
                'max_response_time_ms': round(max_response_time, 2),
                'avg_query_count': round(avg_query_count, 1),
                'runs': endpoint_results
            }

            results.append(result)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Average: {avg_response_time:.2f}ms, {avg_query_count:.1f} queries"
                )
            )

        # Save results to file
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f'\nBenchmark complete! Results saved to {output_file}')
        )

        # Print summary table
        self._print_summary_table(results)

    def _get_or_create_test_user(self):
        """Get or create a test user for benchmarking"""
        email = 'benchmark@test.com'
        username = 'benchmark_user'
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                email=email,
                password='testpass123'
            )
        return user

    def _get_token(self, user):
        """Generate JWT token for user"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def _print_summary_table(self, results):
        """Print a formatted summary table"""
        self.stdout.write('\n' + '=' * 100)
        self.stdout.write(self.style.SUCCESS('BENCHMARK SUMMARY'))
        self.stdout.write('=' * 100)

        # Header
        header = f"{'Endpoint':<40} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} {'Queries':<10}"
        self.stdout.write(header)
        self.stdout.write('-' * 100)

        # Rows
        for result in results:
            avg_time = result['avg_response_time_ms']
            min_time = result['min_response_time_ms']
            max_time = result['max_response_time_ms']
            queries = result['avg_query_count']

            # Color code based on performance
            if avg_time <= 100:
                style = self.style.SUCCESS
            elif avg_time <= 200:
                style = self.style.WARNING
            else:
                style = self.style.ERROR

            row = f"{result['endpoint']:<40} {avg_time:<12.2f} {min_time:<12.2f} {max_time:<12.2f} {queries:<10.1f}"
            self.stdout.write(style(row))

        self.stdout.write('=' * 100)
