import asyncio
import functools
import logging
import time
from typing import Callable, Any

from redis.asyncio import Redis

from core.config.settings import settings
from core.exceptions.resilience import ServiceUnavailableError, BulkheadRejectedError

logger = logging.getLogger(__name__)

# Global registry for bulkheads to share semaphores across function calls if needed
_bulkheads: dict[str, asyncio.Semaphore] = {}

def bulkhead(name: str, max_concurrency: int):
    """Limits concurrent executions per process."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if name not in _bulkheads:
                _bulkheads[name] = asyncio.Semaphore(max_concurrency)
            
            sem = _bulkheads[name]
            if sem.locked():
                raise BulkheadRejectedError(name, max_concurrency)
            
            async with sem:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def circuit_breaker(name: str, failure_threshold: int, recovery_timeout: int):
    """
    Redis-backed circuit breaker.
    If 'failure_threshold' consecutive errors occur, opens the circuit for 'recovery_timeout' seconds.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            cb_key = f"circuit_breaker:{name}"
            
            try:
                state_data = await redis.hgetall(cb_key)
                failures = int(state_data.get("failures", 0))
                last_failure_time = float(state_data.get("last_failure", 0))
                
                if failures >= failure_threshold:
                    time_since_failure = time.time() - last_failure_time
                    if time_since_failure < recovery_timeout:
                        remaining = int(recovery_timeout - time_since_failure)
                        raise ServiceUnavailableError(
                            service_name=name,
                            message=f"{name} is temporarily unavailable (circuit breaker open). Will retry automatically in {remaining} seconds."
                        )
                    else:
                        # HALF-OPEN state: we let this request through to test if service recovered
                        pass

                try:
                    result = await func(*args, **kwargs)
                    
                    # On success, reset if it was previously failing
                    if failures > 0:
                        await redis.delete(cb_key)
                        logger.warning(f"Circuit breaker for {name} CLOSED (service recovered).")
                    
                    return result
                except ServiceUnavailableError:
                    raise
                except Exception as e:
                    # Record failure
                    pipe = redis.pipeline()
                    pipe.hincrby(cb_key, "failures", 1)
                    pipe.hset(cb_key, "last_failure", time.time())
                    pipe.expire(cb_key, recovery_timeout * 2)  # Keep state around long enough
                    results = await pipe.execute()
                    
                    new_failures = results[0]
                    if new_failures == failure_threshold:
                        logger.warning(f"Circuit breaker for {name} OPENED after {new_failures} failures.")
                    
                    raise e
            finally:
                await redis.aclose()
                
        return wrapper
    return decorator
