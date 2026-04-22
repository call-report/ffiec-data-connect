# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-04-22

**First stable release of the 3.x line.** Ships with the same code as
`3.0.0rc6`; there are no behavior differences. This entry exists so
anyone landing on the latest version can see the full scope of 3.0.0
in one place.

Major themes vs. `2.0.5`:

- **SOAP support removed.** The FFIEC SOAP webservice was shut down on
  2026-02-28. `WebserviceCredentials`, `FFIECConnection`, `SOAPAdapter`,
  and their friends are gone; attempting to instantiate them raises
  `SOAPDeprecationError`. REST with `OAuth2Credentials` is the only
  path.
- **Simplified calling convention.** `collect_*(creds, ...)` — no
  `session` argument. The v2-style `session=None, creds=creds` keyword
  form still works (with `DeprecationWarning`) for incremental
  migration.
- **Python 3.11+ required** (was 3.10). Matches pandas 3.0's floor.
- **pandas 3.0 baseline.** `pandas>=3.0.0,<4.0.0` (was `>=1.3.0,<3.0.0`).
- **`output_type="xbrl"` / `"pdf"`** added on `collect_data` and
  `collect_ubpr_facsimile_data` (where XBRL is the only FFIEC-supported
  format) for raw-bytes passthrough.
- **`date_output_format="python_format"` returns tz-aware datetimes**
  labeled `America/New_York` — FFIEC publishes wall-clock DC time with
  no tz marker, so the library attaches one for you. DST honored via
  `zoneinfo`.
- **Silent no-ops promoted to errors** — several v2 parameter
  combinations that did nothing (`output_type="bytes"` on `collect_data`,
  `output_type="polars"` without the extra installed, `date_output_format`
  stubs on three list-returning methods) now raise `ValidationError`.
- **100% REST parity with former SOAP output.** Dual field names
  (`rssd` + `id_rssd`), leading-zero ZIPs preserved, consistent NumPy
  dtypes end-to-end.
- **Async support.** `AsyncCompatibleClient` + `RateLimiter` for
  parallel collection at up to 5× throughput.
- **`FFIECError` exception hierarchy** with structured context,
  opt-in-able via `disable_legacy_mode()` or `FFIEC_USE_LEGACY_ERRORS=false`.
  Legacy `ValueError` mode is the default for v2 back-compat and will
  flip in a future release.

The full per-RC history — `rc1` through `rc6` — remains below for anyone
following along with development.

## [3.0.0rc6] - 2026-04-22

Vestigial-argument audit: warnings on silently-ignored parameter
combinations, completion of a previously-stubbed feature
(`date_output_format`), and a consistency fix for polars-without-polars.

### Added

- **`date_output_format` now actually works** on `collect_reporting_periods`,
  `collect_ubpr_reporting_periods`, and `collect_filers_submission_date_time`.
  The helper that was a no-op stub (`# Future enhancement: ...`) is now
  implemented. `"string_yyyymmdd"` converts `"MM/DD/YYYY"` → `"YYYYMMDD"`;
  `"python_format"` returns a **tz-aware** `datetime` object labeled as
  `America/New_York`. FFIEC emits all of its date/time values in Washington,
  DC local time but sends no tz marker on the wire, so naive datetimes here
  would force every downstream caller to reattach the same timezone. DST is
  handled automatically via `zoneinfo` (EST in winter, EDT in summer). If a
  caller passes an already-tz-aware `datetime` in, its tzinfo is preserved —
  we only label naive values. Shared via a new `_format_date_for_output()`
  helper in `methods_enhanced.py`.
- **`collect_data`'s `quarter` column is also tz-aware under
  `date_output_format="python_format"`.** The XBRL-processing code path in
  `xbrl_processor.py` used a second, parallel date-conversion branch that
  previously returned naive datetimes. Applying the same
  `ZoneInfo("America/New_York")` label there keeps the two code paths
  consistent, so callers can compare a `collect_data` quarter against a
  `collect_filers_submission_date_time` timestamp (or a
  `collect_reporting_periods` entry) without hitting
  `TypeError: can't compare offset-naive and offset-aware datetimes`.
- Shared `_require_polars_available()` helper consolidating the
  "polars extra not installed" check.

### Fixed

- **Silent polars fallback → `ValidationError`.** When `output_type="polars"`
  was requested but the `polars` extra wasn't installed, four methods
  (`collect_reporting_periods`, `collect_filers_since_date`,
  `collect_filers_submission_date_time`, `collect_filers_on_reporting_period`,
  plus `collect_ubpr_reporting_periods`) would silently return a Python
  list instead. Now they raise `ValidationError`, matching `collect_data`'s
  long-standing behavior.
- **Pre-existing `ConnectionError` re-raise bug.** Four spots in
  `methods_enhanced.py` wrapped caught exceptions with
  `raise_exception(ConnectionError, f"...")` — missing the positional
  `message` argument for the typed-exception path, so any error in those
  methods raised `TypeError: ConnectionError.__init__() missing 1
  required positional argument: 'message'` instead of the intended
  `ConnectionError`. Also narrowed the re-raise to skip re-wrapping
  already-typed `FFIECError` subclasses (fixes a separate silent-failure
  where a `ValidationError` from `_require_polars_available()` would be
  swallowed and turned into the same `TypeError`).
- **Stale "endpoint may not be implemented" error text** (two sites —
  `methods.py` and `protocol_adapter.py`). The `RetrieveFacsimile`
  endpoint is implemented and exercised by live integration tests; an
  HTTP 500 there is almost always a transient upstream issue. Message
  now says so and suggests retry.

### Documented

- **`UserWarning` when `force_null_types` / `date_output_format` are passed
  with `output_type="xbrl"` or `"pdf"`.** Raw-bytes outputs bypass parsing,
  so those arguments silently had no effect. The warning surfaces the
  no-op so callers drop the argument (or change `output_type`).
- **`UserWarning` when `force_null_types` is passed to a method with no
  typed null columns** (`collect_reporting_periods`,
  `collect_ubpr_reporting_periods`, `collect_filers_since_date`). The
  parameter is accepted on those methods for API symmetry; warning makes
  the no-op visible at runtime rather than only in the docstring.

### Review follow-ups

Post-review tightening based on parallel code-review + silent-failure hunt:

- `_warn_force_null_types_no_op` is now applied to **all five** methods
  where the parameter is a documented no-op —
  `collect_filers_submission_date_time` and
  `collect_filers_on_reporting_period` were missing the warning in the
  initial rc6 commit and would have been silent drop-through.
- `_format_date_for_output` with `date_output_format="python_format"` now
  raises `ValidationError` on unparseable input instead of silently
  returning a string. The previous behavior would have violated the
  documented return type and broken downstream `.year` / `.month`
  access on any value that didn't round-trip through `strptime`. String
  modes still pass through unchanged (with a `logger.debug` for
  diagnostic trails).
- The narrowed `except Exception` handlers in `methods_enhanced.py` now
  also re-raise `AttributeError` / `KeyError` / `TypeError` untouched.
  Wrapping those as `ConnectionError` would mislead users into thinking
  FFIEC is down when the real problem is a library bug or an API shape
  drift. Only genuinely unexpected (presumed-network) exceptions still
  fall through to the `ConnectionError` wrap.
- Minor legacy-mode behavior change: adapter `ConnectionError` now
  propagates verbatim instead of being re-wrapped with the
  "Failed to retrieve … via REST API: …" prefix. The new message is
  cleaner; flagged here because legacy-mode users may notice.
- **Legacy-error-mode narrowing symmetry.** rc6's initial narrowed
  `except Exception` re-raised `FFIECError` subclasses untouched — but
  that only helps users running with `FFIEC_USE_LEGACY_ERRORS=false`.
  In the default legacy mode, `raise_exception(ValidationError, ...)`
  produces a plain `ValueError`, which wasn't in the re-raise list and
  got wrapped as `"Failed to retrieve … via REST API: …"`. Net effect:
  when a legacy-mode user forgot `pip install 'ffiec-data-connect[polars]'`
  and asked for `output_type="polars"`, they saw a message that read
  like FFIEC was down (`"Failed to retrieve reporting periods via REST
  API: Polars not available"`). The narrowed `except` now also
  re-raises `ValueError` when `use_legacy_errors()` is true, so the
  clean `"Polars not available"` error surfaces in both modes. Applied
  to the same four sites as the prior narrowing.

### Tests

- New `tests/unit/test_rc6_arg_interactions.py` (39 tests) covers every
  warning path, the polars-missing error on each affected method,
  end-to-end date-format conversion on each wired method, unparseable-
  input handling in both string and python-format modes, and the
  programming-error-propagation behavior on the narrowed `except` blocks.
- Updated two pre-existing tests in `test_methods_enhanced.py` and
  `test_protocol_adapter_v3.py` whose asserted behavior changed
  (the date-format stub became real; the 500 message was reworded).
- **786 unit tests pass** (up from 746 in rc5, 711 on main).

## [3.0.0rc5] - 2026-04-22

Hotfix for a regression shipped in rc4 plus a systematic test-coverage audit
of every meaningful kwarg combination on the seven public `collect_*` methods.

### Fixed

- **`collect_*(creds=creds, ...)` pure-kwarg new style no longer raises
  `ValueError: Missing credentials argument`.** rc4's resolver checked only
  the first-positional slot (`creds_or_session`) and skipped straight to an
  error when that slot was unset — even when the caller had correctly
  provided `creds=` as a keyword argument (the natural form after dropping
  the deprecated `session` parameter). The resolver now falls back to the
  `second_arg` slot when the first is unset: it returns the credentials on
  `OAuth2Credentials`, raises `SOAPDeprecationError` on
  `WebserviceCredentials`, and raises `ValidationError` only when truly
  nothing was provided.

  ```python
  # Now works (was broken in rc4):
  periods = collect_reporting_periods(creds=creds, series="call")
  ```

### Test coverage

rc4's regression reached users because the test suite covered the positional
form (`f(creds, ...)`) and the legacy kwarg form (`f(session=None, creds=creds, ...)`)
but **not** the pure-kwarg new style. rc5 closes every gap in the calling-
convention matrix (~27 new tests):

- New `TestMixedKwargCombinations` class for mid-migration patterns:
  `f(None, creds=creds, ...)` (half-migrated, S4) and `f(creds, session=None, ...)`
  (moved creds positional but hasn't removed `session=None`, S6).
- `TestNewStyleKwargCreds` extended with `test_pure_kwarg_soap_creds_raises`
  (the exact path the rc5 resolver fix introduced — the test that, had it
  existed for rc4, would have caught the regression), `test_creds_none_kwarg_raises_validation_error`
  (common user mistake — forgot to instantiate creds), and
  `test_positional_none_only_raises_validation_error`.
- `TestResolveSessionAndCreds` extended with helper-level coverage for
  `f(creds=soap_creds)`, `f(session=truthy_conn)` alone, and
  `f(creds="not_creds")`.
- `test_pure_kwarg_creds_succeeds_without_warning` strengthened to assert
  the mocked downstream was *called* — the rc4 version of this test passed
  against the bug because its "error message" check was too permissive.
  The tightened assertion would have caught rc4's regression.

All 746 unit tests pass (up from 711 in rc4).

### Documented behavior

- `f(creds, session=<truthy_non_None>, ...)` — a valid positional
  `OAuth2Credentials` combined with a truthy (non-`None`) `session=` kwarg.
  Current behavior: the session is silently discarded and only a
  deprecation warning fires. The positional equivalent `f(conn, creds)`
  raises `SOAPDeprecationError`, so these probably ought to match. Test
  added pinning the current behavior; decision deferred to a separate
  issue.

## [3.0.0rc4] - 2026-04-22

Deprecations, an output-format refactor, and several consistency fixes.

### Added

- **`output_type="xbrl"`** on `collect_data` and `collect_ubpr_facsimile_data`
  — returns raw XBRL XML bytes (UTF-8, starting with `<?xml`). The library
  normalizes the BOM that the FFIEC UBPR endpoint emits so every response
  arrives in a consistent shape.
- **`output_type="pdf"`** on `collect_data` (Call Report series only)
  — returns raw PDF file bytes. Supports the audit-friendly "archive a
  human-readable snapshot per quarter" use case. UBPR endpoint has no PDF
  variant per the FFIEC spec, so `series="ubpr"` with `output_type="pdf"`
  raises `ValidationError`.
- **`force_null_types` parameter on all 7 `collect_*` methods** (was
  previously only on `collect_data` and `collect_ubpr_facsimile_data`).
  Accepted as a documented no-op on methods that return plain lists (no
  typed columns to apply null semantics to) — added for API symmetry so
  callers don't hit `TypeError` when switching between methods.
- **`RESTAdapter.retrieve_facsimile(..., facsimile_format=...)`** now
  accepts `"XBRL"` (default) or `"PDF"`. Previously the `facsimileFormat`
  header was hard-coded to `"XBRL"`.

### Deprecated

- **`OAuth2Credentials(token_expires=...)`** — deprecated no-op. Expiration
  is always decoded from the JWT's `exp` claim (authoritative). Any value
  passed here is discarded after a `DeprecationWarning`.

  ```python
  # Before
  creds = OAuth2Credentials(
      username="user", bearer_token="eyJ...",
      token_expires=datetime.now() + timedelta(days=90),  # guess!
  )

  # After — JWT exp is authoritative
  creds = OAuth2Credentials(username="user", bearer_token="eyJ...")
  ```

- **`session=` keyword argument on `collect_*()` methods** — the documented
  2.x calling convention `collect_reporting_periods(session=None, creds=creds, ...)`
  had started raising `TypeError` in rc1–rc3 after the first parameter
  was renamed internally. It now works again with a `DeprecationWarning`.
  Preferred form:

  ```python
  collect_reporting_periods(creds, series="call")
  ```

- **`output_type="bytes"`** — deprecated alias for `"xbrl"`. Where the one
  method that historically honored it (`collect_ubpr_facsimile_data`) is
  called, the value is translated to `"xbrl"` transparently and a
  `DeprecationWarning` is emitted. On every other method it was already
  misbehaving (returning `None` on `collect_data`, returning a list on
  the other 5) and now raises `ValidationError` after the warning.

- **`session=` keyword argument on `OAuth2Credentials.test_credentials()`**
  — the parameter was a SOAP-era stub and has never been used in the REST
  code path. Passing any value now emits a `DeprecationWarning`; it will
  be removed in a future release.

### Fixed

- `collect_reporting_periods(session=None, creds=creds, ...)` and the
  equivalent calls on all 7 public `collect_*` methods no longer raise
  `TypeError: got an unexpected keyword argument 'session'`.
- `output_type="bytes"` no longer silently misbehaves: `collect_data`
  previously returned `None` (no matching branch) and the 5 list-returning
  methods returned a list. All now either translate to `"xbrl"` (on the
  one supported method) or raise `ValidationError` with a pointer to the
  replacement (`xbrl` / `pdf`).
- UBPR XBRL bytes returned from `retrieve_ubpr_xbrl_facsimile` previously
  carried a leading UTF-8 BOM (`\xef\xbb\xbf`); Call Report XBRL did not.
  The adapter now strips the BOM uniformly so every XBRL response starts
  directly with `<?xml`.

### Internal

- Extracted `_validate_force_null_types()` helper at module top; the
  duplicated 9-line validation block in `collect_data` and
  `collect_ubpr_facsimile_data` is now a single call.
- `_output_type_validator()` takes a `supports: set[str]` keyword and
  returns the normalized output_type (rewriting `"bytes"` → `"xbrl"`
  where back-compat is preserved). Every `collect_*` method now declares
  its supported output types explicitly at its own call site, making
  the contract local and checkable.

## [3.0.0rc3] - 2026-04-21

**Metadata-only pre-release.** No code, test, or public API changes from rc2.

### Changed

- `README.md`: replaced two stale `ffiec-data-connect.readthedocs.io` links
  with the current documentation home at
  https://call.report/library/ffiec-data-connect. README contents are
  bundled into the PyPI long description, so the rc2 project page
  rendered links that pointed at the retired RTD site.

### Notes

- Installable from PyPI (pre-release channel) with
  `pip install --pre ffiec-data-connect` or `ffiec-data-connect==3.0.0rc3`.
- `[project.urls]` already pointed at call.report in rc2; this
  release corrects the long-description text to match.
- All rc2-installed code continues to work unchanged under rc3.

## [3.0.0rc2] - 2026-04-20 — Superseded by rc3

First installable 3.0 pre-release.

### Changed

- `[project.urls]` in `pyproject.toml` repointed from GitHub / RTD to
  https://call.report/library/ffiec-data-connect for `Homepage` and
  `Documentation`, and to
  https://call.report/library/ffiec-data-connect/release-history for
  `Changelog`. `Repository` and `Bug Tracker` remain on GitHub.
- `docs/`: Sphinx narrative RSTs removed; `docs/source/index.rst` now
  renders a single redirect landing so the
  `ffiec-data-connect.readthedocs.io` URL remains a live redirect into
  call.report.
- `docs/source/conf.py`: `extensions = []` — autodoc / napoleon /
  sphinxcontrib-openapi no longer needed with one static page.
- `pyproject.toml [project.optional-dependencies.docs]`: trimmed from
  9 deps to 2 (`sphinx`, `sphinx-rtd-theme`). Removed
  sphinx-autodoc-typehints, myst-parser, sphinxcontrib-openapi, doc8,
  rstcheck, and doc-build pytest deps.

### Known issue (fixed in rc3)

- `README.md` still contained two `ffiec-data-connect.readthedocs.io`
  references which render on the PyPI project page long description.
  Fixed in rc3 — PyPI enforces filename reservation, so the fix
  required a new version number.

## [3.0.0] - 2026-04-09

### Breaking Changes

- **SOAP API support removed**: `WebserviceCredentials` and `FFIECConnection` now raise `SOAPDeprecationError` on instantiation
- **`zeep` and `requests` removed from dependencies**: If your code depended on these transitively, add them to your own project
- **Non-None `session` parameter with OAuth2 credentials now raises `SOAPDeprecationError`**: Previously silently ignored
- **pandas 3.0 is the new baseline**: `pandas>=3.0.0,<4.0.0` (up from `>=1.3.0,<3.0.0`). pandas 2.x and older are no longer supported. Tested against 3.0.2 with 0 deprecation warnings in library code paths.
- **Dependency upper bounds relaxed**:
  - `httpx`: `<1.0.0` → `<2.0.0`
  - `polars`: `<1.0.0` → `<2.0.0`
  - `lxml`: `<6.0.0` → `<7.0.0` (needed for Python 3.14 wheels)
  - `xmltodict`: `<1.0.0` → `<2.0.0`
  - `pyarrow`: `<20.0.0` → `<24.0.0`

### New Features

- **JWT token expiry auto-detected from payload**: `token_expires` parameter is now optional when constructing `OAuth2Credentials`
- **New preferred calling convention**: `collect_*(creds, ...)` without session parameter; the older `collect_*(None, creds, ...)` form still works but emits `DeprecationWarning`
- **`SOAPDeprecationError`** with detailed migration guidance, code examples, and portal URL
- **`MIGRATION.md` and `llms.txt` migration guides** for developers and AI coding assistants
- **Python 3.11 is the new minimum supported version** (up from 3.10, matching pandas 3.0's requirement). Python 3.10 is EOL on 2026-10-04.
- **Python 3.14 officially supported** in the CI test matrix alongside 3.11–3.13
- **100% statement test coverage**: 652 unit + 26 integration tests

### Bug Fixes

- **Fixed `datahelpers._normalize_output_from_reporter_panel`**: missing `State` incorrectly set `city=None` instead of `state=None`
- **Fixed `TypeError` in UBPR error handlers**: `raise_exception` was called with wrong arguments
- **Removed broad `except Exception` blocks in UBPR methods** that reclassified all errors as `ConnectionError`

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

[3.0.0]: https://github.com/call-report/ffiec-data-connect/releases/tag/v3.0.0
[2.0.5]: https://github.com/call-report/ffiec-data-connect/releases/tag/v2.0.5
[2.0.0]: https://github.com/call-report/ffiec-data-connect/releases/tag/v2.0.0
[1.0.0]: https://github.com/call-report/ffiec-data-connect/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/call-report/ffiec-data-connect/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/call-report/ffiec-data-connect/releases/tag/v0.2.0