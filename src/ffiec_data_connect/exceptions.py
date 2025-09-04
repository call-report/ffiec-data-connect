"""Descriptive exceptions for the ffiec_data_connect package

This module provides custom exceptions with detailed error messages
to improve debugging and user experience.
"""

from typing import Any, Dict, Optional, Type


def raise_exception(
    exception_class: Type[Exception], legacy_message: str, *args: Any, **kwargs: Any
) -> None:
    """Raise an exception with legacy compatibility support.

    If legacy mode is enabled, raises ValueError with the legacy message.
    Otherwise, raises the specific exception class.

    Args:
        exception_class: The specific exception class to raise
        legacy_message: Message to use for ValueError in legacy mode
        *args: Arguments for the specific exception
        **kwargs: Keyword arguments for the specific exception
    """
    from ffiec_data_connect.config import use_legacy_errors

    if use_legacy_errors():
        # Legacy mode - raise ValueError with simple message
        raise ValueError(legacy_message)
    else:
        # New mode - raise specific exception with context
        raise exception_class(*args, **kwargs)


class FFIECError(Exception):
    """Base exception for all FFIEC Data Connect errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class NoDataError(FFIECError):
    """Raised when no data is returned from the FFIEC webservice"""

    def __init__(
        self, rssd_id: Optional[str] = None, reporting_period: Optional[str] = None
    ):
        message = "No data returned from FFIEC webservice"
        details = {}
        if rssd_id:
            details["rssd_id"] = rssd_id
        if reporting_period:
            details["reporting_period"] = reporting_period
        super().__init__(message, details)


class CredentialError(FFIECError):
    """Raised when there are issues with credentials"""

    def __init__(self, message: str, credential_source: Optional[str] = None):
        details = {}
        if credential_source:
            details["credential_source"] = credential_source
        super().__init__(message, details)


class ValidationError(FFIECError):
    """Raised when input validation fails"""

    def __init__(self, field: str, value: Any, expected: str):
        message = f"Validation failed for field '{field}'"
        details = {"field": field, "provided_value": str(value), "expected": expected}
        super().__init__(message, details)


class ConnectionError(FFIECError):
    """Raised when connection to FFIEC webservice fails"""

    def __init__(
        self, message: str, url: Optional[str] = None, status_code: Optional[int] = None
    ):
        details: Dict[str, Any] = {}
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)


class RateLimitError(FFIECError):
    """Raised when API rate limit is exceeded"""

    def __init__(self, retry_after: Optional[int] = None):
        message = "FFIEC API rate limit exceeded"
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, details)


class XMLParsingError(FFIECError):
    """Raised when XML/XBRL parsing fails"""

    def __init__(self, message: str, xml_snippet: Optional[str] = None):
        details = {}
        if xml_snippet:
            # Truncate for security
            details["xml_snippet"] = (
                xml_snippet[:200] + "..." if len(xml_snippet) > 200 else xml_snippet
            )
        super().__init__(message, details)


class SessionError(FFIECError):
    """Raised when there are session management issues"""

    def __init__(self, message: str, session_state: Optional[str] = None):
        details = {}
        if session_state:
            details["session_state"] = session_state
        super().__init__(message, details)
