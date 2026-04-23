from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class AsilaException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code

class TenantNotFoundException(AsilaException):
    def __init__(self, tenant_id: str):
        super().__init__(f"Tenant {tenant_id} not found", status.HTTP_404_NOT_FOUND)

async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, AsilaException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "type": exc.__class__.__name__}
        )
    
    if isinstance(exc, SQLAlchemyError):
        logger.error(f"Database error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred", "type": "DatabaseError"}
        )

    # Fallback for all other exceptions
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred", "type": "InternalError"}
    )
