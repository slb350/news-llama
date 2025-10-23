"""
Custom error handlers for News Llama web application.

Provides user-friendly error messages and prevents technical details
from leaking to end users.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging


logger = logging.getLogger(__name__)

# User-friendly error messages (don't expose technical details)
ERROR_MESSAGES = {
    # User service errors
    "user_not_found": "We couldn't find your profile. Please select or create one.",
    "user_validation": "Please check your profile information and try again.",
    # Interest service errors
    "interest_duplicate": "You've already added that interest to your profile.",
    "interest_not_found": "That interest wasn't found in your profile.",
    "interest_validation": "Interest must be between 1 and 100 characters.",
    "interest_too_long": "Interest name is too long (maximum 100 characters).",
    "interest_empty": "Interest name cannot be empty.",
    # Newsletter service errors
    "newsletter_not_found": "Newsletter not found. It may have been deleted.",
    "newsletter_duplicate": "You already have a newsletter for this date. Check your calendar!",
    "newsletter_validation": "Please check your request and try again.",
    # Generation service errors
    "generation_failed": "Newsletter generation failed. We'll automatically retry in a few minutes.",
    "generation_error": "Something went wrong while generating your newsletter. Please try again later.",
    "max_retries": "We tried multiple times but couldn't generate your newsletter. Our team has been notified.",
    # Generic errors
    "server_error": "Something went wrong on our end. Please try again in a few moments.",
    "validation_error": "Please check your input and try again.",
}


def get_friendly_message(exception: Exception) -> str:
    """
    Convert exception to user-friendly message.

    Args:
        exception: The exception that was raised

    Returns:
        User-friendly error message (no technical details)
    """
    # Map specific exceptions to friendly messages
    exception_name = exception.__class__.__name__

    if exception_name == "UserNotFoundError":
        return ERROR_MESSAGES["user_not_found"]
    elif exception_name == "UserValidationError":
        return ERROR_MESSAGES["user_validation"]
    elif exception_name == "DuplicateInterestError":
        return ERROR_MESSAGES["interest_duplicate"]
    elif exception_name == "InterestNotFoundError":
        return ERROR_MESSAGES["interest_not_found"]
    elif exception_name == "InterestValidationError":
        # Check if it's about length
        error_str = str(exception).lower()
        if "100" in error_str or "long" in error_str:
            return ERROR_MESSAGES["interest_too_long"]
        elif "empty" in error_str:
            return ERROR_MESSAGES["interest_empty"]
        return ERROR_MESSAGES["interest_validation"]
    elif exception_name == "NewsletterNotFoundError":
        return ERROR_MESSAGES["newsletter_not_found"]
    elif exception_name == "DuplicateNewsletterError":
        return ERROR_MESSAGES["newsletter_duplicate"]
    elif exception_name == "NewsletterAlreadyExistsError":
        return ERROR_MESSAGES["newsletter_duplicate"]
    elif exception_name == "NewsletterValidationError":
        # Check for specific validation errors
        error_str = str(exception).lower()
        if "max" in error_str or "limit" in error_str:
            return ERROR_MESSAGES["max_retries"]
        # All other validation errors get generic message
        return ERROR_MESSAGES["newsletter_validation"]
    elif exception_name == "GenerationServiceError":
        return ERROR_MESSAGES["generation_failed"]
    elif exception_name == "NewsletterGenerationError":
        return ERROR_MESSAGES["generation_error"]
    else:
        # Generic fallback
        return ERROR_MESSAGES["server_error"]


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler for unexpected errors.

    Prevents stack traces and technical details from leaking to users.
    Logs full exception details for debugging.

    Args:
        request: The FastAPI request
        exc: The unhandled exception

    Returns:
        JSON response with user-friendly error message
    """
    # Log the full exception with traceback for debugging
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
        exc_info=exc,
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
        },
    )

    # Return generic user-friendly message (no technical details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": ERROR_MESSAGES["server_error"],
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with friendly messages.

    Converts technical validation errors into user-friendly format.

    Args:
        request: The FastAPI request
        exc: The validation error

    Returns:
        JSON response with validation error details
    """
    # Log validation error
    logger.warning(
        f"Validation error in {request.method} {request.url.path}: {exc.errors()}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "errors": exc.errors(),
        },
    )

    # Serialize errors properly (remove non-serializable objects from ctx)
    errors = []
    for error in exc.errors():
        # Create clean error dict without non-serializable context
        clean_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": error.get("input"),
        }
        # Only include ctx if it contains serializable data
        if "ctx" in error:
            ctx = error["ctx"]
            clean_ctx = {}
            for key, value in ctx.items():
                # Only include simple types (str, int, float, bool, None)
                if isinstance(value, (str, int, float, bool, type(None))):
                    clean_ctx[key] = value
                else:
                    # Convert complex objects to strings
                    clean_ctx[key] = str(value)
            clean_error["ctx"] = clean_ctx
        errors.append(clean_error)

    # Return validation errors (Pydantic already provides good messages)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
        },
    )
