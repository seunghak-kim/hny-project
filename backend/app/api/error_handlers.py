"""
Error Handlers
Centralized error handling for FastAPI
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
import logging

from app.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 검증 에러 핸들러

    Args:
        request: FastAPI Request
        exc: RequestValidationError

    Returns:
        JSONResponse with error details
    """
    errors = exc.errors()

    # 첫 번째 에러 메시지 추출
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "Invalid input")

    error_response = ErrorResponse(
        error_code="INVALID_INPUT",
        message=f"Validation error in '{field}': {message}",
        details={
            "errors": errors,
            "body": exc.body if hasattr(exc, "body") else None
        },
        timestamp=datetime.now().isoformat()
    )

    logger.warning(
        f"Validation error: {field} - {message} "
        f"(path: {request.url.path})"
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    일반 예외 핸들러

    Args:
        request: FastAPI Request
        exc: Exception

    Returns:
        JSONResponse with error details
    """
    error_response = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        details={
            "error": str(exc),
            "type": type(exc).__name__
        },
        timestamp=datetime.now().isoformat()
    )

    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc} "
        f"(path: {request.url.path})",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


async def value_error_handler(request: Request, exc: ValueError):
    """
    ValueError 핸들러

    Args:
        request: FastAPI Request
        exc: ValueError

    Returns:
        JSONResponse with error details
    """
    error_response = ErrorResponse(
        error_code="VALUE_ERROR",
        message=str(exc),
        details={"type": "ValueError"},
        timestamp=datetime.now().isoformat()
    )

    logger.warning(
        f"ValueError: {exc} (path: {request.url.path})"
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.dict()
    )


async def key_error_handler(request: Request, exc: KeyError):
    """
    KeyError 핸들러 (State 누락 필드 등)

    Args:
        request: FastAPI Request
        exc: KeyError

    Returns:
        JSONResponse with error details
    """
    error_response = ErrorResponse(
        error_code="KEY_ERROR",
        message=f"Required field missing: {str(exc)}",
        details={"type": "KeyError"},
        timestamp=datetime.now().isoformat()
    )

    logger.error(
        f"KeyError: {exc} (path: {request.url.path})",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


def register_error_handlers(app):
    """
    FastAPI 앱에 에러 핸들러 등록

    Args:
        app: FastAPI application instance
    """
    # Pydantic 검증 에러
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 일반 에러
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(KeyError, key_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Error handlers registered")
