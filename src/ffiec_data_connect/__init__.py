"""
FFIEC Data Connect - Python wrapper for FFIEC webservice API.

This package provides secure, thread-safe access to FFIEC financial data
with support for both synchronous and asynchronous operations.
"""

# Version
__version__ = "2.0.0rc4"

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
from ffiec_data_connect.credentials import CredentialType, WebserviceCredentials, OAuth2Credentials
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
)

# SOAP client caching utilities
from ffiec_data_connect.soap_cache import clear_soap_cache, get_cache_stats

# Phase 0 - Data format analysis and normalization (REST API support)
from ffiec_data_connect.data_normalizer import DataNormalizer
from ffiec_data_connect.format_analyzer import APIFormatAnalyzer
from ffiec_data_connect.financial_analyzer import FinancialDataAnalyzer

# Phase 1 - Protocol adapters and enhanced methods
from ffiec_data_connect.protocol_adapter import (
    ProtocolAdapter,
    RESTAdapter,
    SOAPAdapter,
    RateLimiter,
    create_protocol_adapter
)
from ffiec_data_connect.methods_enhanced import EnhancedMethodsHelper

# Phase 2 - Performance benchmarking tools
from ffiec_data_connect.performance_benchmark import (
    PerformanceBenchmark,
    BenchmarkResult,
    ComparisonReport,
    quick_benchmark,
    benchmark_async_client,
    print_performance_report
)

# Phase 2 - Production monitoring and observability
from ffiec_data_connect.monitoring import (
    MetricsCollector,
    PerformanceMonitor,
    MigrationTracker,
    APICallRecord,
    MetricData,
    get_metrics_collector,
    get_performance_monitor,
    get_migration_tracker,
    monitor_api_call,
    record_protocol_usage,
    get_monitoring_summary
)

# Expose main classes for easier import
__all__ = [
    # Core classes
    "WebserviceCredentials",
    "OAuth2Credentials",  # Phase 0 - REST API support
    "FFIECConnection",
    "AsyncCompatibleClient",
    # Methods (backward compatible)
    "collect_reporting_periods",
    "collect_data",
    "collect_filers_since_date",
    "collect_filers_submission_date_time",
    "collect_filers_on_reporting_period",
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
    # Phase 0 - Data format analysis and normalization
    "DataNormalizer",
    "APIFormatAnalyzer", 
    "FinancialDataAnalyzer",
    # Phase 1 - Protocol adapters and enhanced methods
    "ProtocolAdapter",
    "RESTAdapter", 
    "SOAPAdapter",
    "RateLimiter",
    "create_protocol_adapter",
    "EnhancedMethodsHelper",
    # Version
    "__version__",
]
