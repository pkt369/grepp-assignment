"""
Celery tasks for background processing.
"""
import logging
from celery import shared_task
from django.db.models import Count

from tests.models import Test, TestRegistration
from courses.models import Course, CourseRegistration
from common.redis_client import get_redis_client

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def sync_registration_counts(self):
    """
    Synchronize registration counts from Redis to database.

    This task:
    1. Reads the set of updated test/course IDs from Redis
    2. Calculates the actual count for each ID
    3. Updates the count field in the database
    4. Clears the Redis set

    Runs every minute via Celery Beat.
    """
    logger.info("Starting registration count synchronization")

    try:
        redis_client = get_redis_client()
        if not redis_client:
            logger.error("Failed to get Redis client")
            return

        # Sync Test counts
        sync_test_counts(redis_client)

        # Sync Course counts
        sync_course_counts(redis_client)

        logger.info("Registration count synchronization completed")

    except Exception as e:
        logger.error(f"Error in sync_registration_counts: {e}", exc_info=True)
        raise


def sync_test_counts(redis_client):
    """
    Sync test registration counts from Redis to database.

    Args:
        redis_client: Redis client instance
    """
    try:
        # Get updated test IDs from Redis
        test_ids_bytes = redis_client.smembers('test:updated_ids')

        if not test_ids_bytes:
            logger.debug("No test updates to sync")
            return

        # Convert bytes to integers
        test_ids = [int(tid) for tid in test_ids_bytes]
        logger.info(f"Syncing counts for {len(test_ids)} tests")

        # Calculate actual counts using bulk query
        counts = TestRegistration.objects.filter(
            test_id__in=test_ids
        ).values('test_id').annotate(count=Count('id'))

        # Create a dictionary for quick lookup
        count_dict = {item['test_id']: item['count'] for item in counts}

        # Update each test
        updated_count = 0
        for test_id in test_ids:
            real_count = count_dict.get(test_id, 0)
            Test.objects.filter(id=test_id).update(registration_count=real_count)
            updated_count += 1
            logger.debug(f"Updated test {test_id} count to {real_count}")

        # Clear the Redis set
        redis_client.delete('test:updated_ids')
        logger.info(f"Successfully synced {updated_count} test counts")

    except Exception as e:
        logger.error(f"Error syncing test counts: {e}", exc_info=True)
        raise


def sync_course_counts(redis_client):
    """
    Sync course registration counts from Redis to database.

    Args:
        redis_client: Redis client instance
    """
    try:
        # Get updated course IDs from Redis
        course_ids_bytes = redis_client.smembers('course:updated_ids')

        if not course_ids_bytes:
            logger.debug("No course updates to sync")
            return

        # Convert bytes to integers
        course_ids = [int(cid) for cid in course_ids_bytes]
        logger.info(f"Syncing counts for {len(course_ids)} courses")

        # Calculate actual counts using bulk query
        counts = CourseRegistration.objects.filter(
            course_id__in=course_ids
        ).values('course_id').annotate(count=Count('id'))

        # Create a dictionary for quick lookup
        count_dict = {item['course_id']: item['count'] for item in counts}

        # Update each course
        updated_count = 0
        for course_id in course_ids:
            real_count = count_dict.get(course_id, 0)
            Course.objects.filter(id=course_id).update(registration_count=real_count)
            updated_count += 1
            logger.debug(f"Updated course {course_id} count to {real_count}")

        # Clear the Redis set
        redis_client.delete('course:updated_ids')
        logger.info(f"Successfully synced {updated_count} course counts")

    except Exception as e:
        logger.error(f"Error syncing course counts: {e}", exc_info=True)
        raise
