# SPDX-License-Identifier: MPL-2.0
# Copyright 2025-2026 Civic Forge Solutions LLC

"""
FFIEC Data Connect - Python wrapper for FFIEC REST API.

This package provides secure, thread-safe access to FFIEC financial data
via the REST API with OAuth2 authentication.

Note: SOAP API support was removed in v3.0.0. The FFIEC SOAP API was
shut down on February 28, 2026.
"""

# Version
__version__ = "3.0.0"

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
    SOAPDeprecationError,
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

# Protocol adapters (SOAPAdapter is a deprecated stub)
from ffiec_data_connect.protocol_adapter import (
    ProtocolAdapter,
    RESTAdapter,
    SOAPAdapter,
    create_protocol_adapter,
)

# SOAP client caching utilities (deprecated stubs)
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
    "SOAPDeprecationError",
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
