"""
FFIEC Data Connect - Python wrapper for FFIEC webservice API.

This package provides secure, thread-safe access to FFIEC financial data
with support for both synchronous and asynchronous operations.
"""

# Version
__version__ = "0.3.0"

# Core imports - maintain backward compatibility
from ffiec_data_connect.credentials import WebserviceCredentials, CredentialType
from ffiec_data_connect.ffiec_connection import FFIECConnection, ProxyProtocol
from ffiec_data_connect.methods import (
    collect_reporting_periods,
    collect_data,
    collect_filers_since_date,
    collect_filers_submission_date_time,
    collect_filers_on_reporting_period
)
from ffiec_data_connect.exceptions import (
    FFIECError,
    NoDataError,
    CredentialError,
    ValidationError,
    ConnectionError,
    RateLimitError,
    XMLParsingError,
    SessionError
)

# New async-compatible client
from ffiec_data_connect.async_compatible import AsyncCompatibleClient, RateLimiter

# Configuration for legacy compatibility
from ffiec_data_connect.config import (
    use_legacy_errors,
    set_legacy_errors,
    enable_legacy_mode,
    disable_legacy_mode
)

# Expose main classes for easier import
__all__ = [
    # Core classes
    'WebserviceCredentials',
    'FFIECConnection',
    'AsyncCompatibleClient',
    
    # Methods (backward compatible)
    'collect_reporting_periods',
    'collect_data',
    'collect_filers_since_date',
    'collect_filers_submission_date_time',
    'collect_filers_on_reporting_period',
    
    # Enums
    'CredentialType',
    'ProxyProtocol',
    
    # Exceptions
    'FFIECError',
    'NoDataError',
    'CredentialError',
    'ValidationError',
    'ConnectionError',
    'RateLimitError',
    'XMLParsingError',
    'SessionError',
    
    # Utilities
    'RateLimiter',
    
    # Configuration
    'use_legacy_errors',
    'set_legacy_errors',
    'enable_legacy_mode',
    'disable_legacy_mode',
    
    # Version
    '__version__'
]