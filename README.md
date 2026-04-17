# FFIEC Webservice Python Connector

## Purpose

The FFIEC Data Connect Python library allows researchers, analysts, and financial institutions to efficiently access and analyze regulatory banking data from the Federal Financial Institution Examination Council (FFIEC). This library eliminates the complexity of working directly with FFIEC's Webservice APIs by providing a unified, Pythonic interface that handles authentication, data normalization, and protocol differences automatically.

## Overview

The FFIEC Data Connect Python library (`ffiec_data_connect`) downloads data from the FFIEC (Federal Financial Institution Examination Council) via the REST API.

>**`ffiec-data-connect` is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.**

## Key Features

- **REST API Access**: Modern RESTful interface with OAuth2 bearer tokens
- **OAuth2 Authentication**: REST API support with 90-day bearer tokens
- **Higher Rate Limits**: REST API allows 2500 requests/hour
- **Data Normalization**: Ensures consistent data normalization
- **Multiple Output Formats**: Returns data as Python lists, Pandas DataFrames, or Polars DataFrames
- **Field Name Compatibility**: Provides both `rssd` and `id_rssd` field names to support existing code

### Disclaimer

- __Please review the license and disclaimer before using this package.__

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
- All implementations
- All output formats (list, pandas, polars)

## Installation

### Requirements

- Python 3.11 or higher
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
   - Generate a 90-day JWT bearer token from the Account Details tab

> **JWT Token Requirements**: Valid tokens must start with `ey` and end with `.` (e.g., `eyJhbGci...ifQ.`). Tokens expire after **90 days**, and must be manually regenerated via the FFIEC portal. This software does not automatically refresh tokens, and JWT refresh tokens are not supported by FFIEC.

### Using the REST API

```python
from ffiec_data_connect import OAuth2Credentials, collect_data, collect_reporting_periods

# Setup REST API credentials
creds = OAuth2Credentials(
    username="your_username",
    bearer_token="eyJhbGci...",  # JWT token (NOT your password!)
)
# Note: token_expires is auto-detected from the JWT token

# Check if token is expired
if creds.is_expired:
    print("Token is expired - generate a new one!")

# Get reporting periods
periods = collect_reporting_periods(
    creds,
    series="call",
    output_type="list"
)

# Get individual bank data
data = collect_data(
    creds,
    reporting_period="12/31/2023",
    rssd_id="480228",  # JPMorgan Chase
    series="call",
    output_type="pandas",  # Returns DataFrame
    force_null_types="pandas"  # Better integer display (optional)
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
    # Common causes: expired token, invalid JWT format
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
- **RSSD IDs**: Normalized as strings
- **Dates**: Consistent datetime format (MM/DD/YYYY input, configurable output)

### Null Value Handling
The library supports different null value strategies:

```python
# Default: pandas nulls
data = collect_data(...)

# Force pandas nulls (better integer display)
data = collect_data(..., force_null_types="pandas")

# Force numpy nulls (legacy compatibility)
data = collect_data(..., force_null_types="numpy")
```

**Why this matters**: 
- **numpy nulls** (`np.nan`) convert integers to floats (displays as `100.0`)
- **pandas nulls** (`pd.NA`) preserve integer types (displays as `100`)

## Rate Limiting

The REST API has a rate limit of ~2500 requests/hour.

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

### 🎯 Quick Start Examples

```python
from ffiec_data_connect import OAuth2Credentials, collect_data

# Setup
creds = OAuth2Credentials(
    username="your_username",
    bearer_token="eyJhbGci...",  # 90-day JWT token
)
# Note: token_expires is auto-detected from the JWT token

# Get data
data = collect_data(
    creds,
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
- Ensure correct date format: MM/DD/YYYY

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

This library is provided by Civic Forge Solutions LLC under the Mozilla Public License 2.0.

## Commercial Support

`ffiec-data-connect` is free and open-source under MPL 2.0 — you can use it commercially, modify it, and distribute it without any payment or license key. Organizations that want priority support with guaranteed response times, migration assistance, or custom development can purchase an optional commercial support agreement from Civic Forge Solutions LLC.

The commercial offering does not gate any features of the library; it is strictly a support and services agreement for teams that need a formal vendor relationship (common in regulated finance). See [COMMERCIAL.md](COMMERCIAL.md) for what's included, who it's for, and how to get in touch. For inquiries, contact michael@civicforge.solutions.

## Additional Resources

- **Full Documentation**: https://ffiec-data-connect.readthedocs.io/
- **Examples**: Jupyter notebooks included with package
- **Version History**: See CHANGELOG.md
- **REST API Reference**: Comprehensive OpenAPI specification in documentation