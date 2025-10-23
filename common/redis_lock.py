import redis
from django.conf import settings
from contextlib import contextmanager
import time

# Redis 클라이언트 (Lock 전용)
redis_client = redis.Redis.from_url(
    settings.REDIS_LOCK_URL,
    decode_responses=True
)

class RedisLock:
    """Redis 분산 락 구현"""
    
    def __init__(self, key, timeout=10, retry_times=5, retry_delay=0.2):
        """
        Args:
            key: Lock 키
            timeout: Lock 만료 시간 (초)
            retry_times: Lock 획득 재시도 횟수
            retry_delay: 재시도 간격 (초)
        """
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        self.lock_value = None
    
    def acquire(self):
        """Lock 획득"""
        import uuid
        self.lock_value = str(uuid.uuid4())
        
        for _ in range(self.retry_times):
            # SET NX EX: key가 없을 때만 설정하고 만료시간 지정
            acquired = redis_client.set(
                self.key,
                self.lock_value,
                nx=True,  # Not eXists
                ex=self.timeout  # EXpire
            )
            
            if acquired:
                return True
            
            time.sleep(self.retry_delay)
        
        return False
    
    def release(self):
        """Lock 해제 (Lua 스크립트로 원자적 처리)"""
        if not self.lock_value:
            return False
        
        # Lua 스크립트: 자신이 획득한 Lock만 해제
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = redis_client.eval(lua_script, 1, self.key, self.lock_value)
        return bool(result)


@contextmanager
def redis_lock(key, timeout=10, retry_times=5, retry_delay=0.2):
    """
    Context Manager로 Redis Lock 사용
    
    Usage:
        with redis_lock('payment:user:123:test:456'):
            # 임계 영역 코드
            process_payment()
    """
    lock = RedisLock(key, timeout, retry_times, retry_delay)
    
    acquired = lock.acquire()
    if not acquired:
        raise Exception(f"Failed to acquire lock: {key}")
    
    try:
        yield lock
    finally:
        lock.release()