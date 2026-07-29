import asyncio
import functools
import logging
import time
from typing import Callable, Any

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

_circuits: dict[str, dict] = {}

def circuit_breaker(name: str, failure_threshold: int, recovery_timeout: int):
    """
    In-memory circuit breaker.
    If 'failure_threshold' consecutive errors occur, opens the circuit for 'recovery_timeout' seconds.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if name not in _circuits:
                _circuits[name] = {"failures": 0, "last_failure": 0.0}
            
            state = _circuits[name]
            failures = state["failures"]
            last_failure_time = state["last_failure"]
            
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
                if state["failures"] > 0:
                    state["failures"] = 0
                    logger.warning(f"Circuit breaker for {name} CLOSED (service recovered).")
                
                return result
            except ServiceUnavailableError:
                raise
            except Exception as e:
                # Record failure
                state["failures"] += 1
                state["last_failure"] = time.time()
                
                if state["failures"] == failure_threshold:
                    logger.warning(f"Circuit breaker for {name} OPENED after {state['failures']} failures.")
                
                raise e
                
        return wrapper
    return decorator
