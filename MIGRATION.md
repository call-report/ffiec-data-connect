# Migration Guide: ffiec-data-connect v2.x to v3.0

## What Changed and Why

The FFIEC shut down their SOAP API on **February 28, 2026**. All legacy security tokens expired on that date. The REST API is now the only way to access FFIEC data.

Starting with `ffiec-data-connect` v3.0.0:

- **SOAP support has been removed.** `WebserviceCredentials` and `FFIECConnection` raise `SOAPDeprecationError` on instantiation. They remain importable for `isinstance` checks, but cannot be used.
- **`zeep` and `requests` are no longer dependencies.** The REST API uses `httpx`. If your code imported these libraries transitively through `ffiec-data-connect`, you will need to add them to your own dependencies.
- **JWT token expiry is now auto-detected.** `OAuth2Credentials` reads the `exp` claim from the JWT payload automatically. You no longer need to pass `token_expires`. As of 3.0.0rc4, passing `token_expires=...` still works but emits a `DeprecationWarning` and the value is ignored — the JWT's `exp` claim is authoritative.
- **A bug in `datahelpers` was fixed.** When the `State` field was missing from reporter panel data, the library incorrectly set `city=None` instead of `state=None`. This is corrected in v3.0.0.
- **Non-None `session` with OAuth2 credentials now raises.** Previously, passing a stale `FFIECConnection` object to a REST method was silently ignored. Now it raises `SOAPDeprecationError` to surface the mistake.

## Breaking Changes Summary

| What | v2.x behavior | v3.0 behavior |
|------|---------------|---------------|
| `WebserviceCredentials(...)` | Creates SOAP credentials | Raises `SOAPDeprecationError` |
| `FFIECConnection()` | Creates session for SOAP | Raises `SOAPDeprecationError` |
| `collect_*(conn, soap_creds, ...)` | Calls FFIEC SOAP API | Raises `SOAPDeprecationError` |
| `collect_*(conn, oauth2_creds, ...)` | Silently ignores `conn` | Raises `SOAPDeprecationError` (non-None session) |
| `zeep` in dependencies | Included | Removed |
| `requests` in dependencies | Included | Removed |
| Missing `State` in reporter panel | Sets `city=None` (bug) | Sets `state=None` (fixed) |

## Step-by-Step Migration

### 1. Upgrade the library

```bash
pip install --upgrade ffiec-data-connect
```

### 2. Get a REST API bearer token

If you haven't already registered for the REST API:

1. Go to https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx
2. Complete the Microsoft Entra ID registration process. No separate Microsoft account is needed — the FFIEC registration creates it for you. You will receive an invitation email from `invites@microsoft.com`.
3. If the callback link after Microsoft verification fails (this is a common issue), manually navigate to https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx
4. Once logged in, go to the **Account Details** tab and generate a **90-day JWT bearer token**.

The token is a long string that starts with `ey` and ends with `.` (e.g., `eyJhbGci...ifQ.`). Store it securely — an environment variable is recommended:

```bash
export FFIEC_BEARER_TOKEN='eyJhbGci...ifQ.'
```

### 3. Update imports

Method imports (`collect_data`, `collect_reporting_periods`, etc.) are unchanged. Only the credential and connection imports change:

```python
# Before (v2.x)
from ffiec_data_connect import WebserviceCredentials, FFIECConnection

# After (v3.0)
from ffiec_data_connect import OAuth2Credentials
```

If you catch exceptions, `SOAPDeprecationError` is new:

```python
from ffiec_data_connect import SOAPDeprecationError  # new in v3.0
```

### 4. Replace credential creation

```python
# Before (v2.x) — SOAP
conn = FFIECConnection()
creds = WebserviceCredentials(username="your_username", password="your_security_token")

# Before (v2.x) — SOAP via environment variables
conn = FFIECConnection()
# reads FFIEC_USERNAME and FFIEC_PASSWORD from env
creds = WebserviceCredentials()

# After (v3.0) — REST
import os
creds = OAuth2Credentials(
    username="your_username",
    bearer_token=os.environ["FFIEC_BEARER_TOKEN"],
)
# No FFIECConnection needed. Token expiry is auto-detected from the JWT.
```

You can check token status programmatically:

```python
print(creds.token_expires)  # e.g., 2026-07-07 12:37:33
print(creds.is_expired)     # True if token expires within 24 hours
```

### 5. Update method calls

The `session` parameter is no longer needed. Pass credentials as the first argument:

```python
# Before (v2.x)
periods = collect_reporting_periods(conn, creds, series="call")
data = collect_data(conn, creds, "12/31/2025", "480228", "call", output_type="pandas")
filers = collect_filers_on_reporting_period(conn, creds, "12/31/2025")
filer_ids = collect_filers_since_date(conn, creds, "12/31/2025", "1/1/2025")
submissions = collect_filers_submission_date_time(conn, creds, "1/1/2025", "12/31/2025")

# After (v3.0 — preferred)
periods = collect_reporting_periods(creds, series="call")
data = collect_data(creds, "12/31/2025", "480228", "call", output_type="pandas")
filers = collect_filers_on_reporting_period(creds, "12/31/2025")
filer_ids = collect_filers_since_date(creds, "12/31/2025", "1/1/2025")
submissions = collect_filers_submission_date_time(creds, "1/1/2025", "12/31/2025")

# After (v3.0 — also works, deprecated, positional form)
periods = collect_reporting_periods(None, creds, series="call")
data = collect_data(None, creds, "12/31/2025", "480228", "call", output_type="pandas")
filers = collect_filers_on_reporting_period(None, creds, "12/31/2025")
filer_ids = collect_filers_since_date(None, creds, "12/31/2025", "1/1/2025")
submissions = collect_filers_submission_date_time(None, creds, "1/1/2025", "12/31/2025")

# After (v3.0.0rc4 — keyword form also accepted, same DeprecationWarning)
# This matches the calling convention shown in older docs/examples.
periods = collect_reporting_periods(session=None, creds=creds, series="call")
```

> **Note:** The `session` parameter is deprecated in all forms. Passing
> `None` as the first positional argument OR as the `session=` keyword
> still works but emits a `DeprecationWarning`. The preferred calling
> convention is `collect_*(creds, ...)` with no session parameter at all.

All other parameters (`series`, `output_type`, `date_output_format`, `force_null_types`, `rssd_id`, `reporting_period`) are unchanged. Output format is identical.

### 5a. `output_type` changes (new in 3.0.0rc4)

- `output_type="bytes"` is **deprecated**. Where it used to return raw
  XBRL bytes (on `collect_ubpr_facsimile_data`), it now emits a
  `DeprecationWarning` and is translated to `"xbrl"` for back-compat.
  On every other method — where it previously misbehaved silently —
  it now raises `ValidationError` after the warning.
- Two new replacements: `output_type="xbrl"` (raw UTF-8 XBRL XML
  bytes, available on `collect_data` and `collect_ubpr_facsimile_data`)
  and `output_type="pdf"` (raw PDF bytes, `collect_data` only — the
  UBPR endpoint is XBRL-only per the FFIEC spec).
- `force_null_types` is now accepted on all 7 methods (previously only
  `collect_data` and `collect_ubpr_facsimile_data`). On methods that
  return a plain list, it's a documented no-op; the symmetry lets you
  switch methods without hitting `TypeError`.
- `OAuth2Credentials.test_credentials(session=...)` — the `session`
  parameter was a SOAP-era stub and is now deprecated. Drop it from
  your call.

### 6. Use new REST-only endpoints (optional)

v3.0 provides two endpoints that were not available via SOAP:

```python
# UBPR reporting periods
ubpr_periods = collect_ubpr_reporting_periods(creds)

# UBPR XBRL data for a specific institution
ubpr_data = collect_ubpr_facsimile_data(creds, "12/31/2025", "480228")
```

### 7. Remove SOAP-specific code

Delete any of the following from your code — they are no longer functional:

```python
# Delete these
conn = FFIECConnection()
conn.proxy_host = "..."
conn.proxy_port = 8080
conn.proxy_protocol = ProxyProtocol.HTTPS
conn.use_proxy = True

# Delete these calls (they are no-ops that emit DeprecationWarning)
clear_soap_cache()
get_cache_stats()
```

If you were using proxy configuration with the SOAP API, the REST API uses `httpx` which respects standard proxy environment variables:

```bash
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
```

### 8. Update your dependencies (if applicable)

If your project depended on `zeep` or `requests` being installed transitively by `ffiec-data-connect`, add them to your own `requirements.txt` or `pyproject.toml`:

```bash
# Only if YOUR code uses these directly
pip install requests  # if you use requests elsewhere
pip install zeep      # if you use zeep elsewhere
```

## Things That Did Not Change

These all work identically in v3.0:

- **Output formats**: `output_type="list"`, `"pandas"`, `"polars"` produce the same data structures
- **Date input formats**: `MM/DD/YYYY`, `YYYY-MM-DD`, `YYYYMMDD`, `#QYYYY`, `datetime` objects all accepted
- **Dual field names**: Both `rssd` and `id_rssd` are provided in all responses that include RSSD IDs
- **Error handling**: The exception hierarchy (`FFIECError`, `CredentialError`, `ValidationError`, etc.) is unchanged. Legacy error mode (`FFIEC_USE_LEGACY_ERRORS`) still works for REST errors.
- **Null handling**: `force_null_types="numpy"` and `force_null_types="pandas"` behave the same
- **ZIP code preservation**: Leading zeros are maintained (e.g., `"02886"`)

New in v3.0 (non-breaking):

- **Simplified calling convention**: `collect_*(creds, ...)` is now the preferred way to call all public methods. The older `collect_*(None, creds, ...)` form still works but emits a `DeprecationWarning`.

## REST vs SOAP: Key Differences

| Feature | SOAP (removed) | REST (current) |
|---------|----------------|----------------|
| Authentication | Username + security token | Username + 90-day JWT bearer token |
| Token lifecycle | No expiration | 90 days (auto-detected by library) |
| Rate limit | 1,000 requests/hour | 2,500 requests/hour |
| HTTP library | `zeep` + `requests` | `httpx` |
| Session object | `FFIECConnection()` | `None` |
| UBPR endpoints | Not available | Available (`collect_ubpr_*`) |
| Headers | Standard SOAP | Non-standard (`UserID`, `Authentication`) — handled by library |

## Troubleshooting

### "SOAPDeprecationError" when running existing code

Your code is using SOAP classes. Follow the migration steps above. The error message includes a code example showing the exact REST equivalent.

### "Invalid bearer token" or authentication failed

- Verify your token starts with `ey` and ends with `.`
- Check `creds.is_expired` — tokens expire every 90 days
- Make sure you're using the JWT bearer token from the Account Details tab, **not** your website password
- Generate a new token at https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx

### Token expired

```python
if creds.is_expired:
    print(f"Token expired on {creds.token_expires}")
    print("Generate a new token at https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx")
```

### Microsoft Entra ID callback issues

After completing Microsoft verification, the callback link sometimes fails. Navigate directly to https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx to complete login.

### Rate limiting

The REST API allows 2,500 requests per hour. The library includes automatic rate limiting. If you hit the limit, `RateLimitError` is raised with `retry_after` seconds:

```python
from ffiec_data_connect import RateLimitError

try:
    data = collect_data(...)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
```
