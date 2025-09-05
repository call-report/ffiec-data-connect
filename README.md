# FFIEC Webservice Python Connector

## Purpose

The FFIEC Data Connect Python library allows researchers, analysts, and financial institutions to efficiently access and analyze regulatory banking data from the Federal Financial Institution Examination Council (FFIEC). This library eliminates the complexity of working directly with FFIEC's Webservice APIs by providing a unified, Pythonic interface that handles authentication, data normalization, and protocol differences automatically.

## Overview

The FFIEC Data Connect Python library (`ffiec_data_connect`) downloads data from the FFIEC (Federal Financial Institution Examination Council) via both SOAP and REST APIs.

>**`ffiec-data-connect` is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.**

> **Authentication Migration Notice (Effective August 25, 2025)**
> 
> The FFIEC CDR is transitioning to Microsoft Entra ID authentication with optional multifactor authentication (MFA). All users must complete a registration process to migrate their accounts to the new authentication protocol.
> 
> - Legacy SOAP API will remain available until **February 28, 2026**
> - All legacy security tokens will expire on **February 28, 2026**
> - Users must transition to the REST API before this date

## Key Features

- **Dual Protocol Support**: Supports both SOAP (legacy) and REST (new) APIs
- **Automatic Protocol Selection**: Automatically selects the appropriate protocol based on credential type
- **OAuth2 Authentication**: REST API support with 90-day bearer tokens
- **Higher Rate Limits**: REST API allows 2500 requests/hour vs 1000 for SOAP
- **Data Normalization**: Ensures consistency between SOAP and REST responses
- **Multiple Output Formats**: Returns data as Python lists, Pandas DataFrames, or Polars DataFrames
- **Field Name Compatibility**: Provides both `rssd` and `id_rssd` field names to support existing code

### Disclaimer

- __Please review the license and disclaimer before using this package.__

## Overview

The FFIEC Data Connect library provides a Python interface to both the SOAP-based and REST-based FFIEC APIs. As of version 2.0, the library supports:

- **SOAP API**: Traditional webservice interface (uses `WebserviceCredentials`)
- **REST API**: Modern RESTful interface with OAuth2 (uses `OAuth2Credentials`)

The library automatically selects the appropriate protocol based on the credentials you provide.

## Field Name Compatibility

**Important**: Property names were inconsistent in earlier versions of this library. To reduce the need to refactor existing user code, all functions that return RSSD data now provide **both field names** with identical data:

- `"rssd"`: Institution RSSD ID 
- `"id_rssd"`: Institution RSSD ID (same data, different field name)

### Usage Examples

```python
# Both of these work identically:
rssd_id = filer.get("rssd")      
rssd_id = filer.get("id_rssd")   

# Defensive programming (recommended for production):
rssd_id = filer.get("rssd") or filer.get("id_rssd")
```

### Affected Functions

This dual field name support applies to:
- `collect_filers_on_reporting_period()`
- `collect_filers_submission_date_time()` 
- All REST and SOAP implementations
- All output formats (list, pandas, polars)

## Installation

### Requirements

- Python 3.10 or higher
- pip package manager

> **Note**: This library requires modern Python versions. For best compatibility, use Python 3.11+ on macOS/Linux. Windows users may experience SSL certificate issues and should consider using Google Colab, WSL, or a Linux environment.

### Install from PyPI

```bash
pip install ffiec-data-connect
```

## Quickstart

### Setting up Credentials

1. **Create an account** at https://cdr.ffiec.gov/public/PWS/CreateAccount.aspx?PWS=true
   - **No separate Microsoft account required!** The FFIEC registration process creates the necessary Microsoft Entra ID authentication for you
   - You'll receive an invitation email from `invites@microsoft.com`
   
2. **Complete Microsoft Entra ID registration**
   - Accept the invitation and complete the registration process
   - If the callback link fails (common issue), manually navigate to: https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx

3. **Generate credentials**:
   - For **REST API** (Recommended): Generate a 90-day JWT bearer token from the Account Details tab
   - For **SOAP API** (Deprecated): Use your username and Security Token

> **JWT Token Requirements**: Valid tokens must start with `ey` and end with `.` (e.g., `eyJhbGci...ifQ.`). Tokens expire after **90 days**, and must be manually regenerated via the FFIEC portal. This software does not automatically refresh tokens, and JWT refresh tokens are not supported by FFIEC.

### Using the REST API (Recommended)

```python
from ffiec_data_connect import OAuth2Credentials, collect_data, collect_reporting_periods

# Setup REST API credentials
from datetime import datetime, timedelta

creds = OAuth2Credentials(
    username="your_username",
    bearer_token="eyJhbGci...",  # JWT token (NOT your password!)
    token_expires=datetime.now() + timedelta(days=90)
)

# Check if token is expired
if creds.is_expired:
    print("Token is expired - generate a new one!")

# Get reporting periods
periods = collect_reporting_periods(
    session=None,  # REST doesn't need session
    creds=creds,
    series="call",
    output_type="list"
)

# Get individual bank data
data = collect_data(
    session=None,
    creds=creds,
    reporting_period="12/31/2023",  # Both APIs use MM/DD/YYYY format
    rssd_id="480228",  # JPMorgan Chase
    series="call",
    output_type="pandas",  # Returns DataFrame
    force_null_types="pandas"  # Better integer display (optional)
)
```

### Using the SOAP API (Legacy)

```python
from ffiec_data_connect import WebserviceCredentials, FFIECConnection, collect_data

# Setup SOAP API credentials
creds = WebserviceCredentials(
    username="your_username",
    password="your_security_token"  # Note: This is the Security Token, not your password
)

# Create connection
conn = FFIECConnection()

# Get data
data = collect_data(
    session=conn,
    creds=creds,
    reporting_period="12/31/2023",  # SOAP also uses MM/DD/YYYY format
    rssd_id="480228",
    series="call",
    output_type="pandas"
)
```

## REST API Endpoints

The library supports all 7 FFIEC REST API endpoints (per CDR-PDD-SIS-611 v1.10):

1. **RetrieveReportingPeriods** - Get available reporting periods
2. **RetrievePanelOfReporters** - Get institutions that filed
3. **RetrieveFilersSinceDate** - Get filers since specific date
4. **RetrieveFilersSubmissionDateTime** - Get submission timestamps
5. **RetrieveFacsimile** - Get individual bank data (XBRL/PDF/SDF)
6. **RetrieveUBPRReportingPeriods** - Get UBPR reporting periods
7. **RetrieveUBPRXBRLFacsimile** - Get UBPR XBRL data

## Key Differences Between SOAP and REST

| Feature | SOAP API | REST API |
|---------|----------|----------|
| Authentication | Username + Security Token | OAuth2 Bearer Token (JWT) |
| Token Lifecycle | No expiration | 90 days |
| Token Format | Any string | Must start with `ey` and end with `.` |
| Rate Limit | 1000 requests/hour | 2500 requests/hour |
| Date Format | MM/DD/YYYY | MM/DD/YYYY |
| Protocol | SOAP/XML | REST/JSON |
| Headers | Standard SOAP | Non-standard (`UserID`, `Authentication`) |
| Library Used | zeep + requests | httpx |
| Status | ⚠️ **Deprecated Feb 28, 2026** | ✅ **Recommended** |

## Error Handling

The library provides specific exception types for better debugging:

```python
from ffiec_data_connect import (
    CredentialError,    # Authentication issues
    ValidationError,    # Invalid parameters
    RateLimitError,     # Rate limit exceeded
    NoDataError,        # No data found
    ConnectionError,    # Network issues
    FFIECError         # General FFIEC errors
)

try:
    data = collect_data(...)
except CredentialError as e:
    print(f"Authentication failed: {e}")
    # Common causes: expired token, wrong password, invalid JWT format
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
except NoDataError as e:
    print(f"No data available: {e}")
except ValidationError as e:
    print(f"Invalid parameters: {e}")
    # Common causes: wrong RSSD ID, invalid date format, wrong series
```

### Legacy Error Mode

For backward compatibility, legacy error mode (raising `ValueError` for all errors) is enabled by default but deprecated. To use new exception types:

```python
import ffiec_data_connect

# Disable legacy mode for better error handling
ffiec_data_connect.disable_legacy_mode()
```

## Data Formats and Type Handling

The library preserves data integrity and provides flexible null handling:

### Data Preservation
- **ZIP codes**: Preserved as strings with leading zeros
- **RSSD IDs**: Normalized as strings across both APIs
- **Dates**: Consistent datetime format (MM/DD/YYYY input, configurable output)

### Null Value Handling
The library supports different null value strategies:

```python
# Default: numpy nulls (SOAP) or pandas nulls (REST)
data = collect_data(...)

# Force pandas nulls (better integer display)
data = collect_data(..., force_null_types="pandas")

# Force numpy nulls (legacy compatibility)
data = collect_data(..., force_null_types="numpy")
```

**Why this matters**: 
- **numpy nulls** (`np.nan`) convert integers to floats (displays as `100.0`)
- **pandas nulls** (`pd.NA`) preserve integer types (displays as `100`)
- REST API defaults to pandas nulls for better data fidelity
- SOAP API defaults to numpy nulls for backward compatibility

## Rate Limiting

Both APIs have rate limits:
- **SOAP**: ~1000 requests/hour
- **REST**: ~2500 requests/hour

The library includes automatic rate limiting to help stay within these limits.

## Interactive Examples & Jupyter Notebooks

### 📓 Jupyter Notebook Demos

The library includes comprehensive Jupyter notebook tutorials with executable examples:

**🚀 REST API Demo** (`ffiec_data_connect_rest_demo.ipynb`)
- OAuth2 credential setup and token management
- Complete REST API walkthrough with real data
- Performance optimization techniques
- Error handling and troubleshooting
- Advanced features: rate limiting, batch operations

**🔧 SOAP API Demo** (`ffiec_data_connect_soap_demo.ipynb`) 
- Legacy SOAP API implementation
- Credential management for WebserviceCredentials
- Session handling and connection management
- Data collection examples with real banking data
- Migration guidance to REST API

### 🎯 Quick Start Examples

**REST API (Recommended)**
```python
from ffiec_data_connect import OAuth2Credentials, collect_data
from datetime import datetime, timedelta

# Setup
creds = OAuth2Credentials(
    username="your_username",
    bearer_token="eyJhbGci...",  # 90-day JWT token
    token_expires=datetime.now() + timedelta(days=90)
)

# Get data
data = collect_data(
    session=None, creds=creds, 
    reporting_period="12/31/2023", rssd_id="480228",
    series="call", output_type="pandas"
)
```

**SOAP API (Legacy)**
```python
from ffiec_data_connect import WebserviceCredentials, FFIECConnection, collect_data

# Setup  
creds = WebserviceCredentials(username="your_username", password="your_token")
conn = FFIECConnection()

# Get data
data = collect_data(
    session=conn, creds=creds,
    reporting_period="12/31/2023", rssd_id="480228", 
    series="call", output_type="pandas"
)
```

### 📚 Additional Examples

For more examples, see:
- **Jupyter Notebooks**: Included with the package for hands-on learning
- **Documentation Examples**: Complete code snippets in the [full documentation](https://ffiec-data-connect.readthedocs.io/)

## Common Issues and Troubleshooting

### Authentication Issues

**"Invalid bearer token" or Authentication Failed**
- ❌ Using website password instead of JWT token
- ❌ Token expired (check with `creds.is_expired`)  
- ❌ Invalid token format (must start with `ey` and end with `.`)

**Solution**: Generate a new JWT token from your PWS portal

### Migration Issues

**Microsoft Callback Problems**
- After completing Microsoft verification, callback link may fail
- **Solution**: Manually navigate to https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx

**Post-Migration Token Issues**
- Old tokens become invalid immediately after migration
- **Solution**: Generate new JWT token from migrated account

### Data Issues

**Integer Values Show as Decimals (100.0 instead of 100)**
```python
# Solution: Use pandas null handling
data = collect_data(..., force_null_types="pandas")
```

**Empty Datasets**
- Check if institution filed for that period: `collect_filers_on_reporting_period()`
- Verify RSSD ID exists and is active
- Ensure correct date format: MM/DD/YYYY for both APIs

### Technical Issues

**Windows SSL Certificate Issues**
- Use Google Colab, WSL, or Linux environment
- Ensure you're using Python 3.11+

**REST API Header Issues** (handled automatically by library)
- Uses non-standard headers: `UserID` (not `UserId`), `Authentication` (not `Authorization`)

For comprehensive troubleshooting, see the full documentation.

## Support

> **Important**: The FFIEC does NOT provide technical support for this library. FFIEC support is only available for CDR account matters.

**Library Support (Technical Issues)**
- **GitHub Issues**: https://github.com/call-report/ffiec-data-connect/issues
- **Direct Email**: michael@civicforge.solutions  

**FFIEC Support (Account Issues Only)**
- **Email**: cdr.help@cdr.ffiec.gov
- **Scope**: CDR account setup, migration, token generation, Microsoft Entra ID issues

**Commercial Support**
Enhanced support available for commercial entities requiring priority technical support, custom modifications, or integration consulting.

This library is provided by Civic Forge Solutions LLC under the Mozilla Public License 2.0.

## Additional Resources

- **Full Documentation**: https://ffiec-data-connect.readthedocs.io/
- **Examples**: Jupyter notebooks included with package
- **Version History**: See CHANGELOG.md
- **REST API Reference**: Comprehensive OpenAPI specification in documentation