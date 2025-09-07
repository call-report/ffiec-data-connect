# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.5] - 2025-09-07

### 🐛 Bug Fix

- **Fixed Inconsistent Reporting Periods Sorting**: Resolved issue where UBPR series returned older periods while Call Reports returned recent periods (issue #33, reported by @Superdu712)

### 🔄 Breaking Changes & Improvements

- **Consistent Reporting Periods Sorting**: All reporting period functions now return data in ascending chronological order (oldest first)
  - `collect_reporting_periods()` (both SOAP and REST)
  - `collect_ubpr_reporting_periods()` (REST)
  - `collect_reporting_periods_enhanced()` (REST)
- **Date Format Support**: Automatic detection and sorting of both SOAP format (YYYY-MM-DD) and REST format (MM/DD/YYYY)
- **Robust Error Handling**: Graceful fallback when date formats are invalid or mixed

### 🧪 Testing & Quality

- **Comprehensive Test Coverage**: 17 new tests covering date sorting functionality
  - Unit tests for core sorting logic with various date formats
  - Integration tests for all affected functions
  - Edge case handling (empty lists, invalid formats, mixed formats)
  - Chronological order verification tests
- **Backward Compatibility**: All existing tests continue to pass

### 📚 Documentation Updates

- **Demo Notebooks**: Updated both REST and SOAP demo notebooks to clearly show sorted periods
  - Clear labeling of "Oldest periods (first N)" and "Latest periods (last N)"
  - Educational notes explaining the new consistent sorting behavior
- **Function Documentation**: Updated docstrings to reflect sorting behavior

### 🔧 Internal Improvements

- **Utility Function**: Added `_sort_reporting_periods_ascending()` for consistent date sorting
- **Format Preservation**: Original date formats are maintained after sorting
- **Memory Efficient**: Minimal overhead for sorting operations

### 📈 User Impact

- **Predictable Behavior**: Both Call Reports and UBPR periods now follow the same ordering
- **Time Series Friendly**: Ascending order makes it easier to work with time series data
- **API Consistency**: Same behavior across SOAP and REST implementations

## [2.0.3] - 2025-09-05

### 🔧 Documentation Fix

- **ReadTheDocs Build**: Simplified post_build command to resolve persistent shell syntax error
- **Command Simplification**: Replaced complex command substitution with basic echo message
- **Build Stability**: Ensures ReadTheDocs builds complete without shell parsing issues

## [2.0.2] - 2025-09-05

### 🔧 Documentation & Configuration Fixes

- **ReadTheDocs Build**: Fixed shell syntax error in `.readthedocs.yml` post_build command
- **Quote Escaping**: Resolved "Syntax error: end of file unexpected" by properly escaping quotes in shell command substitution
- **Sphinx Compatibility**: Fixed docstring formatting in OAuth2Credentials class for proper Sphinx rendering
- **Build Stability**: Ensures ReadTheDocs builds complete without shell syntax errors

## [2.0.1] - 2025-09-05

### 🔧 Documentation Fix

- **ReadTheDocs Build**: Fixed docstring formatting in OAuth2Credentials class that was causing ReadTheDocs build failures
- **Sphinx Compatibility**: Changed from markdown-style code blocks (```) to reStructuredText-style (::) for proper Sphinx rendering
- **Documentation Quality**: Ensures documentation builds cleanly without errors or warnings

## [2.0.0] - 2025-09-05

### 🎉 Major Release - REST API Support & Dual Protocol Architecture

This major release introduces comprehensive REST API support alongside the existing SOAP implementation, OAuth2 authentication, and enterprise-grade features. This version represents a complete overhaul with dual protocol support, providing a seamless migration path from the legacy SOAP API to the modern REST API.

### 🌟 Major New Features

#### REST API Support
- **Complete REST API Implementation**: Full support for all 7 FFIEC REST API endpoints
- **OAuth2 Authentication**: JWT bearer token authentication with 90-day lifecycle
- **Protocol Adapter Pattern**: Automatic protocol selection based on credential type
- **Enhanced Rate Limits**: 2500 requests/hour for REST vs 1000 for SOAP
- **Modern HTTP Client**: Uses httpx for improved performance and reliability

#### Dual Protocol Architecture
- **Automatic Protocol Detection**: Seamlessly switches between SOAP/REST based on credentials
- **Unified API Interface**: Same methods work with both protocols
- **Data Normalization**: Consistent data format regardless of protocol
- **Migration Path**: Easy transition from legacy SOAP to modern REST

### 🔐 Authentication & Security

#### OAuth2Credentials Class
- **JWT Token Support**: Secure JWT bearer token authentication for REST API
- **Token Validation**: Automatic format validation (must start with `ey`, end with `.`)
- **Expiration Tracking**: Built-in token expiration monitoring (90-day lifecycle)
- **Security Masking**: Credentials are masked in string representations

#### Enhanced SOAP Security  
- **WebserviceCredentials**: Improved legacy authentication with security token
- **Credential Immutability**: Credentials cannot be modified after initialization
- **Session Security**: Secure SOAP client caching and session management

#### Microsoft Entra ID Integration
- **Migration Support**: Full support for FFIEC's transition to Microsoft authentication
- **Account Setup Documentation**: Comprehensive guides for new and migrating users
- **Troubleshooting**: Detailed solutions for common migration issues

### 🚀 Enhanced Features

#### Advanced Data Processing
- **force_null_types Parameter**: Choose between numpy and pandas null handling
- **Improved Integer Display**: Pandas nulls preserve integer types (100 vs 100.0)
- **Protocol-Specific Defaults**: REST uses pandas nulls, SOAP uses numpy nulls
- **Data Type Consistency**: Maintains type integrity across protocol boundaries
- **Field Name Compatibility**: All functions provide both 'rssd' and 'id_rssd' fields for backward compatibility

#### Comprehensive Error Handling
- **Protocol-Specific Errors**: Different error types for REST vs SOAP issues
- **JWT Token Errors**: Specific validation for token format and expiration
- **Migration Errors**: Targeted error handling for account migration issues
- **Rate Limiting**: Intelligent rate limit detection and retry logic

#### Enhanced Documentation System
- **Comprehensive Sphinx Documentation**: Professional documentation with RTD hosting
- **OpenAPI Specification**: Reverse-engineered REST API specification
- **Troubleshooting Guide**: Extensive solutions for common issues
- **Account Setup Guide**: Step-by-step Microsoft Entra ID migration instructions
- **Development Guide**: Full development environment setup documentation

### 🏗️ Architecture Improvements

#### Protocol Adapter Pattern
- **RESTAdapter**: Handles all REST API interactions with OAuth2 credentials
- **SOAPAdapter**: Manages legacy SOAP interactions with webservice credentials  
- **Unified Interface**: Same method signatures work with both protocols
- **Automatic Selection**: Protocol chosen based on credential type provided

#### Enhanced Methods System
- **methods.py**: Legacy SOAP methods with backward compatibility
- **methods_enhanced.py**: Modern REST methods with full feature support
- **Protocol Bridging**: Seamless data flow between SOAP and REST implementations
- **Consistent Return Types**: Same data structures regardless of protocol

### 📊 REST API Endpoints

All 7 FFIEC REST API endpoints now supported:
- **RetrieveReportingPeriods**: Get available reporting periods for data series
- **RetrievePanelOfReporters**: Get institutions that filed for specific periods  
- **RetrieveFilersSinceDate**: Get institutions that filed since a specific date
- **RetrieveFilersSubmissionDateTime**: Get detailed submission timestamps
- **RetrieveFacsimile**: Get individual institution data (XBRL/PDF/SDF formats)
- **RetrieveUBPRReportingPeriods**: Get UBPR-specific reporting periods
- **RetrieveUBPRXBRLFacsimile**: Get UBPR XBRL data for institutions

### 🧠 Memory & Performance

#### Async Support
- **AsyncCompatibleClient**: Full async/await support with rate limiting and concurrency control
- **Parallel Processing**: Collect data from multiple banks simultaneously 
- **Thread Pool Executor**: Efficient resource management for concurrent operations
- **Rate Limiting**: Configurable request rate limiting to respect API limits
- **Context Managers**: Automatic resource cleanup with `async with` support

#### XML Processing Optimizations
- **Memory-Efficient Parsing**: Reduced memory copies during XBRL processing
- **Direct Byte Processing**: Parse XML directly from bytes when possible
- **Error Snippet Optimization**: Only decode XML snippets for error reporting
- **Secure XML Processing**: XXE attack prevention with defusedxml integration

#### Connection Management
- **SOAP Client Caching**: Intelligent caching prevents expensive client recreation
- **Session Reuse**: Automatic session cleanup and resource management
- **Thread-Safe Operations**: Safe parallel access to FFIEC webservice
- **Connection Pooling**: Efficient resource utilization for multiple requests

### 📚 Comprehensive Documentation

#### Professional Documentation Suite
- **Sphinx Documentation**: Full API documentation with cross-references
- **ReadTheDocs Hosting**: Professional online documentation at ffiec-data-connect.readthedocs.io
- **OpenAPI Specification**: Complete REST API specification with request/response schemas
- **Interactive Examples**: Comprehensive Jupyter notebooks with real-world use cases

#### User Guides
- **Account Setup Guide**: Microsoft Entra ID migration and token generation
- **Development Setup Guide**: Complete development environment configuration
- **Troubleshooting Guide**: Solutions for authentication, migration, and data issues
- **Data Type Handling Guide**: Complete documentation of null handling and type preservation

### 🧪 Testing & Quality

#### Comprehensive Test Suite
- **250+ Tests**: Unit, integration, and performance tests covering all functionality
- **Protocol Testing**: Separate test suites for SOAP and REST implementations
- **OAuth2 Testing**: Complete JWT token validation and expiration testing  
- **Memory Leak Testing**: Automated detection of memory issues and cleanup validation
- **Thread Safety Testing**: Concurrent access validation across all components
- **Async Integration Testing**: Full async workflow validation with rate limiting

#### Code Quality
- **Type Hints**: Complete type annotation coverage with py.typed marker
- **Code Formatting**: Black, isort, and flake8 integration for consistent style
- **Documentation Standards**: Comprehensive docstrings following Google style
- **Security Testing**: Credential masking and XXE prevention validation

### 🏭 Production Readiness

#### Public Release Preparation
- **Repository Cleanup**: Removed all debug files and credentials from version history
- **Security Audit**: Complete credential sanitization and security review
- **CI/CD Pipeline**: GitHub Actions with comprehensive testing and quality checks
- **Package Distribution**: Modern pyproject.toml with proper dependency management

#### Enterprise Features
- **Commercial Support**: Available priority support and custom development
- **Production Deployment**: Battle-tested with real-world financial institutions
- **Monitoring Integration**: Built-in logging and performance monitoring capabilities
- **Scalability**: Designed for high-volume data collection scenarios

### 🔄 Breaking Changes

#### Python Version Requirements
- **Minimum Python 3.10**: Modern Python features required for optimal performance
- **Recommended Python 3.11+**: Best compatibility and performance on macOS/Linux

#### New Dependencies
- **httpx**: Modern HTTP client for REST API interactions
- **defusedxml**: Secure XML processing with XXE attack prevention
- **Optional polars**: High-performance data processing (install with `pip install ffiec-data-connect[polars]`)

#### Configuration Changes
- **force_null_types Parameter**: New parameter for controlling null value handling
- **Protocol-Specific Defaults**: Different default null types for SOAP vs REST
- **Enhanced Error Types**: Richer exception hierarchy (legacy mode still available)

### 📈 Migration from 1.x

#### Backward Compatibility
- **Existing SOAP Code**: All existing SOAP-based code continues to work unchanged
- **Same Method Signatures**: collect_data(), collect_reporting_periods() unchanged
- **Legacy Error Mode**: ValueError exceptions maintained for compatibility

#### New Capabilities
```python
# New REST API usage
from ffiec_data_connect import OAuth2Credentials
from datetime import datetime, timedelta

# OAuth2 credentials for REST API
rest_creds = OAuth2Credentials(
    username="your_username",
    bearer_token="eyJhbGci...",  # JWT token from FFIEC portal
    token_expires=datetime.now() + timedelta(days=90)
)

# Same methods work with both credential types
data = collect_data(
    session=None,  # None for REST, connection object for SOAP
    creds=rest_creds,  # OAuth2 for REST, Webservice for SOAP
    reporting_period="12/31/2023",
    rssd_id="480228",
    series="call",
    force_null_types="pandas"  # New parameter for null handling
)

# Check token status
if rest_creds.is_expired:
    print("Token expires within 24 hours - time to renew!")
```

### 🎯 FFIEC API Evolution Support

#### Microsoft Entra ID Transition
- **Complete Migration Support**: Handles FFIEC's transition to Microsoft authentication
- **Dual Authentication**: Supports both legacy and new authentication methods
- **Migration Troubleshooting**: Comprehensive solutions for common migration issues
- **Future-Proof**: Ready for SOAP API deprecation in February 2026

#### REST API Compliance
- **CDR-PDD-SIS-611 v1.10**: Full compliance with FFIEC REST API specification
- **Non-Standard Headers**: Handles FFIEC's unique header requirements (`UserID`, `Authentication`)
- **Error Handling**: Proper handling of FFIEC-specific error responses
- **Rate Limiting**: Respects FFIEC rate limits (1000/hour SOAP, 2500/hour REST)

### 🌍 Platform Support

#### Cross-Platform Compatibility
- **macOS/Linux**: Full native support with optimal performance
- **Windows**: Supported with SSL configuration guidance
- **Cloud Platforms**: Tested on Google Colab, AWS, Azure, and GCP
- **Container Ready**: Docker-friendly with minimal dependencies

#### Deployment Options
- **Local Development**: Complete development environment setup
- **Production Deployment**: Enterprise-grade deployment patterns
- **Cloud Integration**: Ready for serverless and containerized deployments
### 🙏 Acknowledgments

This release represents a significant milestone in making FFIEC financial data accessible to researchers, analysts, and financial institutions. Special thanks to the community for feedback and testing that helped shape this comprehensive release.

---

## Previous Releases

## [1.0.0] - 2024-12-XX (Superseded by 2.0.0)

### Added  
- Initial async support and thread safety improvements
- Basic Polars integration
- Enhanced error handling
- Memory leak prevention

## [0.3.0] - 2024-XX-XX

### Added
- Direct XBRL to Polars conversion
- NumPy dtype consistency improvements
- Enhanced notebook demonstrations

### Fixed
- Memory management issues
- Thread safety improvements
- Connection stability

## [0.2.0] - Earlier versions

### Added
- Basic FFIEC webservice integration (SOAP only)
- Pandas DataFrame support
- Core data collection methods

### Features
- collect_data() method
- collect_reporting_periods() method
- WebserviceCredentials class
- FFIECConnection class

---

[2.0.0]: https://github.com/call-report/ffiec-data-connect/releases/tag/v2.0.0
[1.0.0]: https://github.com/call-report/ffiec-data-connect/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/call-report/ffiec-data-connect/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/call-report/ffiec-data-connect/releases/tag/v0.2.0