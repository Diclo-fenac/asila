class DependencyError(Exception):
    """Base class for all dependency-related resilience errors."""
    pass

class ServiceUnavailableError(DependencyError):
    """Raised when a circuit breaker is open or a service is unreachable."""
    def __init__(self, service_name: str, message: str):
        self.service_name = service_name
        self.message = message
        super().__init__(message)

class BulkheadRejectedError(DependencyError):
    """Raised when a service has reached its maximum concurrent capacity."""
    def __init__(self, service_name: str, max_concurrency: int):
        self.service_name = service_name
        self.max_concurrency = max_concurrency
        super().__init__(f"{service_name} is at capacity ({max_concurrency}/{max_concurrency} concurrent requests). Try again in a few seconds.")
