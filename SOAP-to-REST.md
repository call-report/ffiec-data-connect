# Migrating from SOAP to REST API

## Why This Migration Is Required

The FFIEC shut down the SOAP API on **February 28, 2026**. All legacy security tokens expired on that date. The REST API is now the only supported protocol.

Starting with `ffiec-data-connect` v3.0.0, SOAP classes (`WebserviceCredentials`, `FFIECConnection`) raise `SOAPDeprecationError` on instantiation.

## Step 1: Get REST API Credentials

1. Log in at https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx
2. Complete Microsoft Entra ID registration if you haven't already (no separate Microsoft account required -- the FFIEC registration creates it for you)
3. Go to **Account Details** tab and generate a **90-day JWT bearer token**
4. Store the token securely (environment variable recommended)

> **Token format**: Must start with `ey` and end with `.` (e.g., `eyJhbGci...ifQ.`). The library now auto-detects token expiry from the JWT payload, so `token_expires` is optional.

## Step 2: Update Imports

No changes needed for method imports. Only the credential class changes:

```python
# Before (SOAP)
from ffiec_data_connect import WebserviceCredentials, FFIECConnection

# After (REST)
from ffiec_data_connect import OAuth2Credentials
```

## Step 3: Update Credential Creation

```python
# Before (SOAP)
conn = FFIECConnection()
creds = WebserviceCredentials(username="your_username", password="your_security_token")

# After (REST)
creds = OAuth2Credentials(
    username="your_username",
    bearer_token="eyJhbGci...",  # 90-day JWT token from FFIEC portal
)
# token_expires is auto-detected from JWT -- no need to set manually
```

## Step 4: Update Method Calls

The only change is replacing `conn` (or `session`) with `None`:

### collect_reporting_periods

```python
# Before
periods = collect_reporting_periods(conn, creds, series="call")

# After
periods = collect_reporting_periods(None, creds, series="call")
```

### collect_data

```python
# Before
data = collect_data(conn, creds, "12/31/2025", "480228", "call", output_type="pandas")

# After
data = collect_data(None, creds, "12/31/2025", "480228", "call", output_type="pandas")
```

### collect_filers_since_date

```python
# Before
filers = collect_filers_since_date(conn, creds, "12/31/2025", "1/1/2025")

# After
filers = collect_filers_since_date(None, creds, "12/31/2025", "1/1/2025")
```

### collect_filers_submission_date_time

```python
# Before
submissions = collect_filers_submission_date_time(conn, creds, "1/1/2025", "12/31/2025")

# After
submissions = collect_filers_submission_date_time(None, creds, "1/1/2025", "12/31/2025")
```

### collect_filers_on_reporting_period

```python
# Before
filers = collect_filers_on_reporting_period(conn, creds, "12/31/2025")

# After
filers = collect_filers_on_reporting_period(None, creds, "12/31/2025")
```

### collect_ubpr_reporting_periods (REST-only, new)

```python
periods = collect_ubpr_reporting_periods(None, creds)
```

### collect_ubpr_facsimile_data (REST-only, new)

```python
data = collect_ubpr_facsimile_data(None, creds, "12/31/2025", "480228")
```

## Step 5: Remove SOAP-Specific Code

Delete these from your code -- they are no longer needed:

- `FFIECConnection()` instances and all proxy configuration
- `clear_soap_cache()` / `get_cache_stats()` calls
- `conn.proxy_host = ...` / `conn.use_proxy = True` etc.

## Common Gotchas

| Topic | Detail |
|-------|--------|
| Token expiry | JWT tokens expire every 90 days. The library auto-detects expiry from the JWT payload. Check `creds.is_expired` before making calls. |
| Rate limits | REST allows 2500 requests/hour (vs SOAP's 1000). Built-in rate limiting is included. |
| Output format | Output is identical between SOAP and REST. `DataNormalizer` ensures backward compatibility. |
| Field names | Both `rssd` and `id_rssd` are still provided for backward compatibility. |
| Date format | Both APIs use `MM/DD/YYYY`. The library accepts multiple input formats. |
| session=None | Pass `session=None` explicitly. Don't pass old `FFIECConnection` objects. |
| Non-standard headers | The REST API uses `UserID` (not `UserId`) and `Authentication` (not `Authorization`). The library handles this automatically. |
