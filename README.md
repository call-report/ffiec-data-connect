# FFIEC Data Connector

The FFIEC Data Connect Python library (`ffiec_data_connect`) downloads data from the FFIEC (Federal Financial Institution Examination Council) via both SOAP and REST APIs.

**The SOAP API is being deprecated by FFIEC in 2026. Users are advised to transition to the REST API before this date.**

## Key Features

- **Dual Protocol Support**: Supports both SOAP (legacy) and REST (new) APIs
- **Automatic Protocol Selection**: Automatically selects the appropriate protocol based on credential type
- **OAuth2 Authentication**: REST API support with 90-day bearer tokens
- **Higher Rate Limits**: REST API allows 2500 requests/hour vs 1000 for SOAP
- **Data Normalization**: Ensures consistency between SOAP and REST responses
- **Multiple Output Formats**: Returns data as Python lists, Pandas DataFrames, or Polars DataFrames

### Disclaimer

- __This package and documentation is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.__
- __Please review the license and disclaimer before using this package.__

## Overview

The FFIEC Data Connect library provides a Python interface to both the SOAP-based and REST-based FFIEC APIs. As of version 2.0, the library supports:

- **SOAP API**: Traditional webservice interface (uses `WebserviceCredentials`)
- **REST API**: Modern RESTful interface with OAuth2 (uses `OAuth2Credentials`)

The library automatically selects the appropriate protocol based on the credentials you provide.

## Installation

```bash
pip install ffiec-data-connect
```

## Quickstart

### Setting up Credentials

1. Create an account at https://cdr.ffiec.gov/public/PWS/CreateAccount.aspx
2. Login at https://cdr.ffiec.gov/Public/PWS/Login.aspx
3. For **SOAP API**: Use your username and Security Token from the Account Details tab
4. For **REST API**: Generate a 90-day bearer token from the Account Details tab

### Using the REST API (Recommended)

```python
from ffiec_data_connect import OAuth2Credentials, collect_data, collect_reporting_periods

# Setup REST API credentials
creds = OAuth2Credentials(
    username="your_username",
    bearer_token="your_90_day_token"
)

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
    reporting_period="2023-12-31",
    rssd_id="480228",  # JPMorgan Chase
    series="call",
    output_type="pandas"  # Returns DataFrame
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
    reporting_period="2023-12-31",
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
| Authentication | Username + Security Token | OAuth2 Bearer Token |
| Token Lifecycle | No expiration | 90 days |
| Rate Limit | 1000 requests/hour | 2500 requests/hour |
| Protocol | SOAP/XML | REST/JSON |
| Library Used | zeep + requests | httpx |
| All Endpoints Available | Yes | Yes (as of v2.0) |

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
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
except NoDataError as e:
    print(f"No data available: {e}")
```

### Legacy Error Mode

For backward compatibility, legacy error mode (raising `ValueError` for all errors) is enabled by default but deprecated. To use new exception types:

```python
import ffiec_data_connect

# Disable legacy mode for better error handling
ffiec_data_connect.disable_legacy_mode()
```

## Data Formats

The library preserves data integrity:
- **ZIP codes**: Preserved as strings with leading zeros
- **RSSD IDs**: Normalized as strings across both APIs
- **Dates**: Consistent datetime format

## Rate Limiting

Both APIs have rate limits:
- **SOAP**: ~1000 requests/hour
- **REST**: ~2500 requests/hour

The library includes automatic rate limiting to help stay within these limits.

## Examples

See the included Jupyter notebooks for comprehensive examples:
- `ffiec_data_connect_REST_demo.ipynb` - REST API examples
- `ffiec_data_connect_demo.ipynb` - SOAP API examples

## Troubleshooting

### Windows SSL Issues
Some Windows installations may have SSL certificate issues. Consider using:
- Google Colab
- Linux/Mac environment
- WSL (Windows Subsystem for Linux)

### Invalid Format String Error
Ensure you're using version >= 0.2.7 which includes Windows compatibility fixes.

### REST API Header Requirements
The REST API has specific header requirements:
- `UserID` (not `UserId`) 
- `Authentication` (not `Authorization`)
- All parameters passed as headers, not query parameters

## Support

This library is provided by Civic Forge Solutions LLC under the Mozilla Public License 2.0.

For issues, please visit: https://github.com/call-report/ffiec-data-connect

## Changelog

See CHANGELOG.md for version history and updates.