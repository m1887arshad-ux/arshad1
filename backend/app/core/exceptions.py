"""
Secure exception handling to prevent information leakage.

SECURITY PRINCIPLE: Don't expose internal details to users.
Use generic error messages externally, detailed logging internally.

OWASP: A01:2021 - Broken Access Control
       A09:2021 - Security Logging and Monitoring Failures
"""
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class BusinessError:
    """Business-domain exceptions with safe (non-leaky) messages."""

    @staticmethod
    def not_found(resource: str = "Resource", reason: str = "") -> HTTPException:
        """
        Generic 404 that doesn't confirm resource existence.
        
        SECURITY: Returns same response whether resource doesn't exist,
        or user lacks permission. This prevents IDOR enumeration attacks.
        
        Example:
            if not action:
                raise BusinessError.not_found("Action")
        """
        if reason:
            logger.warning(f"Access denied / not found: {resource} - {reason}")
        
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",  # Generic (doesn't leak existence)
        )

    @staticmethod
    def unauthorized(reason: str = "") -> HTTPException:
        """
        Generic 401 for all authentication failures.
        
        SECURITY: Same response for wrong password, non-existent user, etc.
        Prevents user enumeration attacks.
        """
        logger.warning(f"Unauthorized access attempt: {reason}")
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @staticmethod
    def forbidden(reason: str = "") -> HTTPException:
        """
        Generic 403 for permission/ownership issues.
        
        SECURITY: Same response as 404 in sensitive cases to prevent IDOR.
        """
        logger.warning(f"Forbidden access: {reason}")
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    @staticmethod
    def bad_request(detail: str) -> HTTPException:
        """
        400 for input validation / business logic errors.
        
        OK to include specific details here since user caused the issue.
        Examples: "Email already registered", "Quantity must be positive"
        """
        logger.info(f"Bad request: {detail}")
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    @staticmethod
    def conflict(detail: str) -> HTTPException:
        """
        409 for resource conflicts.
        Example: "Email already registered"
        """
        logger.info(f"Conflict: {detail}")
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    @staticmethod
    def server_error(original_error: Exception = None) -> HTTPException:
        """
        Generic 500 - logs actual error internally, hides from user.
        
        SECURITY: Never expose stack traces, SQL errors, or internal paths to users.
        """
        if original_error:
            logger.error(
                f"Internal server error: {type(original_error).__name__}: {str(original_error)}",
                exc_info=True
            )
        else:
            logger.error("Internal server error occurred", exc_info=True)
        
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again later.",  # Generic
        )

    @staticmethod
    def rate_limit_exceeded(detail: str = "Too many requests") -> HTTPException:
        """
        429 - Too many requests (rate limiting).
        """
        logger.warning(f"Rate limit exceeded: {detail}")
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )
