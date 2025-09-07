"""
FFIEC Data Connect - Python wrapper for FFIEC webservice API.

This package provides secure, thread-safe access to FFIEC financial data
with support for both REST and SOAP APIs.
"""

# Version
__version__ = "2.0.5"

# New async-compatible client
from ffiec_data_connect.async_compatible import AsyncCompatibleClient, RateLimiter

# Configuration for legacy compatibility
from ffiec_data_connect.config import (
    disable_legacy_mode,
    enable_legacy_mode,
    set_legacy_errors,
    use_legacy_errors,
)

# Core imports - maintain backward compatibility
from ffiec_data_connect.credentials import (
    CredentialType,
    OAuth2Credentials,
    WebserviceCredentials,
)

# REST API support - Data normalization for backward compatibility
from ffiec_data_connect.data_normalizer import DataNormalizer
from ffiec_data_connect.exceptions import (
    ConnectionError,
    CredentialError,
    FFIECError,
    NoDataError,
    RateLimitError,
    SessionError,
    ValidationError,
    XMLParsingError,
)
from ffiec_data_connect.ffiec_connection import FFIECConnection, ProxyProtocol
from ffiec_data_connect.methods import (
    collect_data,
    collect_filers_on_reporting_period,
    collect_filers_since_date,
    collect_filers_submission_date_time,
    collect_reporting_periods,
    collect_ubpr_facsimile_data,
    collect_ubpr_reporting_periods,
)

# REST API support - Protocol adapters for automatic SOAP/REST selection
from ffiec_data_connect.protocol_adapter import (
    ProtocolAdapter,
    RESTAdapter,
    SOAPAdapter,
    create_protocol_adapter,
)

# SOAP client caching utilities
from ffiec_data_connect.soap_cache import clear_soap_cache, get_cache_stats

# Expose main classes for easier import
__all__ = [
    # Core classes
    "WebserviceCredentials",
    "OAuth2Credentials",  # REST API support
    "FFIECConnection",
    "AsyncCompatibleClient",
    # Methods (backward compatible)
    "collect_reporting_periods",
    "collect_data",
    "collect_filers_since_date",
    "collect_filers_submission_date_time",
    "collect_filers_on_reporting_period",
    # UBPR methods (REST API only)
    "collect_ubpr_reporting_periods",
    "collect_ubpr_facsimile_data",
    # Enums
    "CredentialType",
    "ProxyProtocol",
    # Exceptions
    "FFIECError",
    "NoDataError",
    "CredentialError",
    "ValidationError",
    "ConnectionError",
    "RateLimitError",
    "XMLParsingError",
    "SessionError",
    # Utilities
    "RateLimiter",
    # Configuration
    "use_legacy_errors",
    "set_legacy_errors",
    "enable_legacy_mode",
    "disable_legacy_mode",
    # SOAP Caching
    "clear_soap_cache",
    "get_cache_stats",
    # REST API support
    "DataNormalizer",
    "ProtocolAdapter",
    "RESTAdapter",
    "SOAPAdapter",
    "create_protocol_adapter",
    # Version
    "__version__",
]
