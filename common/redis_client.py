"""
Redis utilities for tracking entity updates.
"""
import logging
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


def get_redis_client():
    """
    Get Redis connection for count tracking.
    Uses default cache connection.
    """
    try:
        return get_redis_connection('default')
    except Exception as e:
        logger.error(f"Failed to get Redis connection: {e}")
        return None


def mark_test_updated(test_id):
    """
    Mark a test as updated by adding its ID to the Redis set.
    This set will be processed by the sync task to update registration counts.

    Args:
        test_id: The ID of the test that was updated
    """
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.sadd('test:updated_ids', test_id)
            logger.debug(f"Marked test {test_id} as updated in Redis")
    except Exception as e:
        # Don't raise exception - count sync is not critical
        logger.warning(f"Failed to mark test {test_id} as updated: {e}")


def mark_course_updated(course_id):
    """
    Mark a course as updated by adding its ID to the Redis set.
    This set will be processed by the sync task to update enrollment counts.

    Args:
        course_id: The ID of the course that was updated
    """
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.sadd('course:updated_ids', course_id)
            logger.debug(f"Marked course {course_id} as updated in Redis")
    except Exception as e:
        # Don't raise exception - count sync is not critical
        logger.warning(f"Failed to mark course {course_id} as updated: {e}")
