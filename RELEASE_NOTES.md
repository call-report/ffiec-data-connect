# Release Notes

`ffiec-data-connect` is a Python library for accessing FFIEC regulatory banking data (Call Reports and UBPR) through the modern REST API. It provides clean, typed access to reporting periods, panels of reporters, and financial facsimile data for researchers, analysts, and financial institutions.

## v3.0.0

_Released 2026-04-09_

### SOAP API removed

The FFIEC is shutting down the legacy SOAP webservice on **February 28, 2026**. Version 3.0.0 completes the transition by removing SOAP support entirely. Attempting to instantiate `WebserviceCredentials` or `FFIECConnection` now raises `SOAPDeprecationError` with inline migration guidance.

**Migration in two steps:**

```python
# Before (v2.x)
from ffiec_data_connect import WebserviceCredentials, FFIECConnection, collect_data
creds = WebserviceCredentials("user", "password")
conn = FFIECConnection()
data = collect_data(conn, creds, "12/31/2024", "480228", "call")

# After (v3.0.0)
from ffiec_data_connect import OAuth2Credentials, collect_data
creds = OAuth2Credentials(username="user", bearer_token="eyJhbGci...")
data = collect_data(creds, "12/31/2024", "480228", "call")
```

Generate a JWT bearer token from the FFIEC portal, drop the `FFIECConnection()` object, and you're done. See [MIGRATION.md](./MIGRATION.md) for the full migration guide, including troubleshooting and code examples.

### What's new

- Cleaner calling convention: `collect_data(creds, ...)` is now preferred. The older session-first form `collect_data(None, creds, ...)` still works but emits a `DeprecationWarning`.
- JWT expiry is auto-detected from the token payload. The `token_expires` parameter on `OAuth2Credentials` is now optional.
- `SOAPDeprecationError` provides detailed migration guidance, code examples, and the FFIEC portal URL when legacy code paths are hit.
- New `MIGRATION.md` and `llms.txt` guides for developers and AI coding assistants.
- 100% statement test coverage: 606 unit tests + 26 integration tests.

### Dependency changes

- **Python 3.11 is now the minimum version** — up from 3.10. This matches pandas 3.0's own requirement; there is no way to support pandas 3.0 and Python 3.10 together. Python 3.10 reaches end-of-life on 2026-10-04.
- **pandas 3.0 is now the baseline** — `pandas>=3.0.0,<4.0.0` (up from `>=1.3.0,<3.0.0`). If you're on pandas 2.x or earlier, upgrade before installing. The full 652-test unit suite and 24-test live integration suite pass against pandas 3.0.2 with zero deprecation warnings from our code.
- `zeep` and `requests` removed from dependencies. If your project imported them transitively through this library, add them to your own `pyproject.toml`.
- Upper bounds relaxed across the board to allow modern major versions:
  - `httpx`: `<1.0.0` → `<2.0.0`
  - `polars`: `<1.0.0` → `<2.0.0`
  - `lxml`: `<6.0.0` → `<7.0.0` (needed for Python 3.14 wheels)
  - `xmltodict`: `<1.0.0` → `<2.0.0`
  - `pyarrow`: `<20.0.0` → `<24.0.0`
- **Python 3.14 officially supported** in the CI test matrix.

### Bug fixes

- Fixed `datahelpers._normalize_output_from_reporter_panel` where a missing `State` field incorrectly nulled `city` instead of `state`.
- Fixed `TypeError` in UBPR error handlers caused by `raise_exception` being called with wrong arguments.
- Removed broad `except Exception` blocks in UBPR methods that were reclassifying all errors as `ConnectionError`.

## v2.0.5

_Released 2025-09-07_

- Fixed inconsistent reporting periods sorting: UBPR series previously returned oldest-first while Call Reports returned newest-first (issue #33).
- All reporting period functions now return dates in **ascending chronological order** (oldest first), across SOAP and REST, for both Call Reports and UBPR.
- Automatic detection of both SOAP (`YYYY-MM-DD`) and REST (`MM/DD/YYYY`) date formats with graceful fallback for invalid or mixed formats.
- Updated demo notebooks to clearly label "oldest" vs "latest" periods.

## v2.0.1 – v2.0.4

_Released 2025-09-05_

- ReadTheDocs build fixes. No user-facing code changes.

## v2.0.0

_Released 2025-09-05_

Major release introducing REST API support alongside the legacy SOAP implementation.

- Full REST API support for all 7 FFIEC REST endpoints (reporting periods, panel of reporters, facsimile retrieval, UBPR, etc.).
- OAuth2 / JWT bearer token authentication via new `OAuth2Credentials` class, with 90-day token lifecycle tracking.
- Protocol adapter pattern automatically selects SOAP or REST based on credential type, so the same `collect_*` methods work with either protocol.
- Higher rate limits on REST (2500 req/hr vs. 1000 req/hr on SOAP).
- `AsyncCompatibleClient` for parallel data collection with built-in rate limiting.
- `force_null_types` parameter to choose between numpy and pandas null handling; pandas nulls preserve integer types.
- Dual field names (`rssd` and `id_rssd`) on all responses for backward compatibility.
- XXE-safe XML parsing via `defusedxml`.
- Minimum Python version raised to 3.10.

---

## Full changelog

For the complete version history including all internal changes, bug fixes, and development notes, see [CHANGELOG.md](./CHANGELOG.md).
