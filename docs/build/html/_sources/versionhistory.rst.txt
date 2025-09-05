Version History
===============

Version 2.0.0 - Major Release
==============================
Date: 2025-09-05

**🎯 Production Release with REST API Support**

Major release introducing comprehensive REST API support, OAuth2 authentication, and dual protocol architecture.

**🔄 Recent Updates**

* **Comprehensive Test Suite**: Added 30+ new tests for OAuth2, force_null_types, and protocol adapters
* **Enhanced Documentation**:
  - Microsoft Entra ID migration instructions and troubleshooting
  - REST API reference with complete OpenAPI specification
  - Comprehensive troubleshooting guide for common issues
  - Updated Python 3.10+ requirement throughout documentation
* **API Refinements**:
  - Added ``force_null_types`` parameter to override default null handling
  - Improved JWT token validation with proper length and format checking
  - Enhanced error messages and validation feedback
* **Developer Experience**:
  - Updated development setup instructions
  - Added reverse-engineered OpenAPI schema integration
  - Fixed GitHub URLs to use call-report organization

**🎉 Major Features**

This release provides a complete dual-protocol implementation supporting both the modern REST API and legacy SOAP API, with seamless migration capabilities.

**🚀 New Features**

* **REST API Support**: Full support for modern OAuth2-based REST API alongside legacy SOAP
* **AsyncCompatibleClient**: Full async/await support with rate limiting and concurrency control
* **Parallel Processing**: Collect data from multiple banks simultaneously
* **Direct Polars Conversion**: XBRL → Polars pipeline preserves maximum numerical precision
* **Advanced Error Handling**: Custom exception types with rich context
* **Memory Management**: Proper cleanup, context managers, SOAP client caching
* **Thread Safety**: Race condition resolution and concurrent access support
* **Null Type Control**: New ``force_null_types`` parameter for pandas/numpy null handling
* **New Collection Methods**:
  - ``collect_filers_on_reporting_period()``
  - ``collect_filers_since_date()``
  - ``collect_filers_submission_date_time()``

**🔒 Security Improvements**

* Comprehensive input validation for all method parameters
* Credential security with password masking
* XXE prevention with XML parser hardening
* Immutable credentials after initialization
* Secure session management

**🧠 Performance & Reliability**

* Memory leak prevention with proper resource cleanup
* SOAP client caching to prevent expensive recreation
* Thread-safe operations throughout
* Up to 5x performance improvement with async operations
* Comprehensive test suite with 253 tests

**📊 Data Processing Enhancements**

* Type-specific columns (int_data, float_data, bool_data, str_data)
* NumPy dtype consistency throughout data pipeline
* Support for list, pandas DataFrame, and Polars DataFrame outputs
* Maximum precision preservation in XBRL processing

**📚 Documentation & Developer Experience**

* Comprehensive Jupyter notebook demonstration
* Technical analysis documents for security, memory, and performance
* Complete API documentation with examples
* Migration guides and backward compatibility

**🔧 Breaking Changes**

While backward compatibility is maintained, some advanced usage patterns may need updates. See CHANGELOG.md for detailed migration guidance.

Version 0.3.0
-------------
Date: 2024-XX-XX

**What's new?**

* Direct XBRL to Polars conversion implementation
* NumPy dtype consistency improvements
* Enhanced notebook demonstrations
* Memory management improvements
* Thread safety enhancements
* Connection stability improvements

Version 0.2.0
-------------
Date: 2020-07-28

**What's new?**

* Fixed issues where credentials provided as environment variables were triggering an exception when used
* Improved error handling and validation
* Enhanced session management

Version 0.1.0
-------------
Date: 2020-07-27

* Initial release (beta)
* Basic FFIEC webservice integration
* Core data collection functionality
