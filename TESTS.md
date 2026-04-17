# Test Catalog

**652 unit tests, 26 integration tests** | 100% statement coverage, ~99.7% total

## Running Tests

```bash
# Unit tests only (no credentials needed)
pytest tests/unit/ -v

# Integration tests (requires FFIEC credentials)
FFIEC_USERNAME=... FFIEC_BEARER_TOKEN='eyJ...' pytest tests/integration/test_rest_api_live.py -v

# Full suite with coverage
FFIEC_USERNAME=... FFIEC_BEARER_TOKEN='eyJ...' pytest tests/ --cov=src/ffiec_data_connect --cov-report=term-missing
```

## Skipped Tests

| Test | Reason |
|------|--------|
| `test_documentation_build.py::test_sphinx_build_html` | Skipped when Sphinx is not installed or docs source directory not found |
| `test_documentation_build.py::test_sphinx_build_linkcheck` | Skipped when Sphinx is not installed |
| `test_documentation_build.py::test_rst_linting_with_doc8` | Skipped when doc8 is not installed |
| `test_documentation_build.py::test_rst_syntax_with_rstcheck` | Skipped when rstcheck is not installed |
| `test_rest_api_live.py::*` (all 26 tests) | Skipped when `FFIEC_USERNAME` and `FFIEC_BEARER_TOKEN` env vars are not set |

## Expected Failures (xfail)

| Test | Reason |
|------|--------|
| `test_rest_api_live.py::test_date_format_yyyymmdd` | `date_output_format` not yet implemented in REST enhanced path |
| `test_rest_api_live.py::test_date_format_python` | `date_output_format` not yet implemented in REST enhanced path |

---


### `tests/unit/test_async_compatible.py`

_Comprehensive unit tests for async_compatible.py with async functionality focus._


**TestRateLimiter** — Test rate limiting functionality.

- `test_rate_limiter_initialization` — Test rate limiter initialization.
- `test_rate_limiter_sync_blocking` — Test synchronous rate limiting with blocking.
- `test_rate_limiter_async_blocking` — Test asynchronous rate limiting with blocking.
- `test_rate_limiter_thread_safety` — Test that rate limiter is thread safe.

**TestAsyncCompatibleClientInitialization** — Test client initialization and configuration.

- `test_client_initialization_defaults` — Test default initialization.
- `test_client_initialization_custom_params` — Test initialization with custom parameters.
- `test_client_initialization_no_rate_limit` — Test initialization with rate limiting disabled.
- `test_connection_caching_raises_for_soap` — Test that _get_connection raises SOAPDeprecationError since FFIECConnection is deprecated.

**TestSynchronousMethods** — Test backward-compatible synchronous methods.

- `test_collect_data_sync` — Test synchronous collect_data method.
- `test_collect_reporting_periods_sync` — Test synchronous collect_reporting_periods method.
- `test_collect_data_with_rate_limiting` — Test that rate limiting is applied to sync methods.

**TestParallelMethods** — Test parallel processing methods.

- `test_collect_data_parallel` — Test parallel data collection.
- `test_collect_data_parallel_with_errors` — Test parallel data collection with some errors.
- `test_collect_data_parallel_progress_callback` — Test progress callback functionality.
- `test_collect_time_series` — Test time series collection for single bank.

**TestAsyncMethods** — Test async/await methods.

- `test_collect_data_async` — Test async data collection.
- `test_collect_batch_async` — Test async batch collection.
- `test_collect_batch_async_with_progress` — Test async batch with progress callback.
- `test_collect_batch_async_with_async_progress` — Test async batch with async progress callback.
- `test_collect_time_series_async` — Test async time series collection.

**TestContextManagers** — Test context manager support.

- `test_sync_context_manager` — Test synchronous context manager.
- `test_async_context_manager` — Test asynchronous context manager.

**TestResourceManagement** — Test resource cleanup and management.

- `test_close_method` — Test explicit resource cleanup.
- `test_executor_cleanup_owned` — Test executor cleanup when owned by client.
- `test_executor_cleanup_not_owned` — Test executor cleanup when provided externally.
- `test_connection_cleanup_error_handling` — Test that connection cleanup errors are handled gracefully.

**TestThreadSafety** — Test thread safety of the client.

- `test_concurrent_data_collection` — Test concurrent data collection.

**TestPerformanceAndMemory** — Test performance characteristics and memory usage.

- `test_parallel_performance` — Test that parallel processing improves performance.
- `test_memory_cleanup_on_close` — Test that close() properly cleans up memory.

**TestRateLimitingIntegration** — Test rate limiting integration with client methods.

- `test_rate_limiting_in_parallel_collection` — Test rate limiting applied during parallel collection.
- `test_async_rate_limiting` — Test rate limiting in async methods.

**TestErrorHandling** — Test error handling and edge cases.

- `test_invalid_credentials_type` — Test error handling for invalid credentials.
- `test_method_call_exception_handling` — Test exception handling in method calls.
- `test_parallel_partial_failure_recovery` — Test recovery from partial failures in parallel processing.

**TestCollectTimeSeries** — Tests for collect_time_series error handling (lines 279-280).

- `test_error_dict_when_future_raises` — When future.result() raises, should return error dict (lines 279-280).

**TestAsyncCallbackHandling** — Tests for async callback handling (lines 369-372).

- `test_sync_callback_on_error` — Sync callback should be called even on error (line 372).
- `test_async_callback_on_error` — Async callback should be called on error (lines 369-370).

**TestAsyncTimeSeriesError** — Tests for async time series error handling (lines 414-415).

- `test_error_in_async_time_series` — Errors in collect_time_series_async should produce error dicts (lines 414-415).

**TestExecutorShutdownInClose** — Tests for executor shutdown in close() (line 431).

- `test_owned_executor_shutdown_called` — close() should call executor.shutdown when client owns the executor (line 431/446).
- `test_non_owned_executor_not_shutdown` — close() should NOT call executor.shutdown when externally provided.

**TestRESTClientBranches** — Tests for REST client branches in collect_data and collect_reporting_periods.

- `test_collect_data_rest_client_passes_none_conn` — REST client should pass None as connection (line 127).
- `test_collect_reporting_periods_rest_client` — REST client should pass None as connection (line 166/171).
- `test_collect_reporting_periods_with_rate_limiter` — Rate limiter should be applied in collect_reporting_periods (line 165).

**TestProgressCallbackOnErrorInParallel** — Test progress_callback is called on error in collect_data_parallel (line 231).

- `test_progress_callback_called_on_error` — When a future raises, progress_callback should be called with error dict (line 231).

**TestRateLimiterInTimeSeries** — Test rate_limiter.wait_if_needed is called in collect_time_series (line 262).

- `test_rate_limiter_called_in_time_series` — Rate limiter should be called for each period in collect_time_series (line 262).

**TestRateLimiterInBatchAsync** — Test rate_limiter in collect_batch_async (line 349).

- `test_rate_limiter_called_in_batch_async` — Rate limiter should be called for each RSSD in collect_batch_async (line 349).

**TestExecutorShutdownOwnedReal** — Test executor shutdown in close() with a real owned executor (line 446).

- `test_close_shuts_down_real_owned_executor` — Create client without external executor, then close(). Executor should be shut down.

### `tests/unit/test_async_integration.py`

_Comprehensive async integration test suite for FFIEC Data Connect._


**TestAsyncBasicFunctionality** — Test basic async functionality and integration.

- `test_async_client_basic_usage` — Test basic async client usage patterns.
- `test_async_data_collection_basic` — Test basic async data collection.
- `test_async_batch_collection_basic` — Test basic async batch collection.
- `test_async_time_series_basic` — Test basic async time series collection.

**TestAsyncRateLimiting** — Test async rate limiting functionality.

- `test_async_rate_limiter_timing` — Test that async rate limiter properly delays calls.
- `test_async_client_rate_limiting` — Test rate limiting in async client operations.
- `test_concurrent_rate_limited_batches` — Test concurrent batch operations with rate limiting.

**TestAsyncConcurrencyPatterns** — Test async concurrency patterns and behavior.

- `test_asyncio_gather_pattern` — Test asyncio.gather pattern with FFIEC client.
- `test_asyncio_as_completed_pattern` — Test asyncio.as_completed pattern with FFIEC client.
- `test_async_semaphore_integration` — Test integration with asyncio semaphores for custom concurrency control.
- `test_async_timeout_handling` — Test timeout handling in async operations.

**TestAsyncFrameworkIntegration** — Test integration with async frameworks and patterns.

- `test_fastapi_like_integration` — Test FastAPI-like integration pattern.
- `test_django_channels_like_integration` — Test Django Channels-like WebSocket integration pattern.
- `test_background_task_processing` — Test background task processing patterns.

**TestAsyncErrorHandling** — Test error handling in async contexts.

- `test_async_error_propagation` — Test that errors are properly propagated in async context.
- `test_async_partial_batch_failure` — Test handling of partial failures in async batch operations.
- `test_async_graceful_shutdown_with_errors` — Test graceful shutdown even when operations are failing.

**TestAsyncPerformancePatterns** — Test performance patterns and optimizations in async context.

- `test_async_vs_sync_performance_comparison` — Compare async vs sync performance for parallel operations.
- `test_async_memory_efficiency_under_load` — Test memory efficiency of async operations under load.
- `test_async_connection_reuse_efficiency` — Test that async operations efficiently reuse connections.

### `tests/unit/test_basic_functionality.py`

_Basic unit tests for FFIEC Data Connect improvements._


**TestSecurity** — Test security improvements.

- `test_credentials_raise_soap_deprecation` — Test that WebserviceCredentials raises SOAPDeprecationError.
- `test_connection_raises_soap_deprecation` — Test that FFIECConnection raises SOAPDeprecationError.
- `test_descriptive_errors` — Test that SOAPDeprecationError provides helpful migration info.

**TestValidation** — Test input validation improvements.

- `test_rssd_validation` — Test RSSD ID validation.

**TestAsyncCapabilities** — Test async and parallel processing capabilities.

- `test_async_client_basic` — Test basic async client functionality.
- `test_parallel_processing` — Test parallel data collection.
- `test_rate_limiting` — Test that rate limiting works.
- `test_async_methods` — Test async method execution.

### `tests/unit/test_credentials.py`

_Comprehensive unit tests for credentials.py with security focus._


**TestWebserviceCredentialsInitialization** — Test that WebserviceCredentials raises SOAPDeprecationError on any instantiation.

- `test_init_with_explicit_credentials_raises_soap_deprecation` — Test that initialization with explicit username and password raises SOAPDeprecationError.
- `test_init_from_environment_raises_soap_deprecation` — Test that initialization from environment variables raises SOAPDeprecationError.
- `test_explicit_overrides_environment_raises_soap_deprecation` — Test that explicit credentials also raise SOAPDeprecationError.
- `test_missing_credentials_raises_soap_deprecation` — Test that missing credentials still raise SOAPDeprecationError (before any validation).
- `test_missing_password_only_raises_soap_deprecation` — Test that missing password still raises SOAPDeprecationError.
- `test_missing_username_only_raises_soap_deprecation` — Test that missing username still raises SOAPDeprecationError.

**TestWebserviceCredentialsSOAPDeprecationMessage** — Test that the SOAPDeprecationError contains useful migration guidance.

- `test_deprecation_error_mentions_oauth2` — Test that the deprecation error mentions OAuth2Credentials as the replacement.
- `test_deprecation_error_soap_method_name` — Test that the deprecation error identifies the deprecated method.
- `test_deprecation_error_has_code_example` — Test that the deprecation error includes a migration code example.

**TestWebserviceCredentialsClassStillExists** — Test that WebserviceCredentials class shell remains for isinstance checks.

- `test_class_is_importable` — Test that WebserviceCredentials can still be imported.
- `test_class_is_a_type` — Test that WebserviceCredentials is still a class.

**TestCredentialSecurity** — Test security aspects of credential handling (using SOAPDeprecationError).

- `test_webservice_credentials_cannot_be_instantiated` — Confirm that all instantiation paths raise SOAPDeprecationError.
- `test_webservice_credentials_no_args_cannot_be_instantiated` — Confirm no-arg instantiation raises SOAPDeprecationError.

**TestCredentialImmutability** — Test credential immutability for security (SOAPDeprecationError blocks init).

- `test_cannot_instantiate_to_modify` — Test that WebserviceCredentials cannot even be instantiated.
- `test_immutability_thread_safety` — Test that instantiation raises SOAPDeprecationError from multiple threads.

**TestCredentialValidation** — Test that WebserviceCredentials raises SOAPDeprecationError before any validation.

- `test_validation_blocked_by_deprecation` — Test that credential validation is blocked because init raises SOAPDeprecationError.
- `test_validation_blocked_for_bad_credentials` — Test that even bad credentials raise SOAPDeprecationError before validation.

**TestCredentialTypes** — Test credential type enumeration and detection.

- `test_credential_type_enum_values` — Test CredentialType enum values.
- `test_credential_source_detection_init_raises_deprecation` — Test that credential source detection for init raises SOAPDeprecationError.
- `test_credential_source_detection_env_raises_deprecation` — Test that credential source detection for environment raises SOAPDeprecationError.

**TestThreadSafety** — Test thread safety of credential operations.

- `test_concurrent_credential_creation_raises_deprecation` — Test concurrent credential creation all raise SOAPDeprecationError.

**TestEdgeCases** — Test edge cases and error conditions.

- `test_empty_string_credentials_raises_deprecation` — Test that empty string credentials raise SOAPDeprecationError.
- `test_none_credentials_raises_deprecation` — Test that None credentials raise SOAPDeprecationError.
- `test_whitespace_credentials_raises_deprecation` — Test that whitespace-only credentials raise SOAPDeprecationError.
- `test_very_long_credentials_raises_deprecation` — Test that very long credentials raise SOAPDeprecationError.
- `test_unicode_credentials_raises_deprecation` — Test that Unicode credentials raise SOAPDeprecationError.

**TestOAuth2CredentialsJWTExpiryAutoDetection** — Test the JWT expiry auto-detection feature of OAuth2Credentials.

- `test_jwt_expiry_extracted_when_no_token_expires_provided` — OAuth2Credentials with no token_expires but a valid JWT extracts exp from payload.
- `test_explicit_token_expires_takes_precedence` — When token_expires is explicitly provided, it takes precedence over JWT exp.
- `test_jwt_without_exp_claim_returns_none` — A JWT without an exp claim results in token_expires being None.

**TestOAuth2CredentialsCoverage** — Additional tests for full coverage of OAuth2Credentials.

- `test_empty_username_raises_credential_error` — OAuth2Credentials with empty string username raises CredentialError (line 82).
- `test_whitespace_only_username_raises_credential_error` — OAuth2Credentials with whitespace-only username raises CredentialError.
- `test_is_expired_when_token_expires_is_none` — is_expired returns False when token_expires is None (line 167).
- `test_test_credentials_expired_token_returns_false` — test_credentials() returns False for expired token (lines 201-211).
- `test_test_credentials_valid_token_returns_true` — test_credentials() returns True for valid token (lines 201-211).
- `test_str_expired_token_shows_expired` — __str__ with expired token shows 'EXPIRED' (line 221).
- `test_str_valid_token_shows_days` — __str__ with valid token shows days remaining (line 226).
- `test_mask_sensitive_string_short` — _mask_sensitive_string with len<=2 returns all asterisks (line 234, 236).
- `test_mask_sensitive_string_normal` — _mask_sensitive_string with normal len shows first and last char (line 236).
- `test_mask_sensitive_string_empty` — _mask_sensitive_string with empty string returns '***' (line 234).
- `test_extract_jwt_expiry_invalid_base64` — _extract_jwt_expiry with invalid base64 payload returns None (lines 263-265).
- `test_extract_jwt_expiry_overflow_exp` — _extract_jwt_expiry with overflow exp value returns None (lines 273-277).
- `test_setattr_immutability_after_init` — Setting a public attribute after init raises CredentialError (line 286).
- `test_repr_delegates_to_str` — __repr__ returns same result as __str__.

**TestOAuth2CredentialsMissingCoverage** — Additional tests to cover remaining uncovered lines in credentials.py.

- `test_test_credentials_empty_username_returns_false` — test_credentials() returns False when username is empty (line 202).
- `test_test_credentials_empty_token_returns_false` — test_credentials() returns False when bearer_token is empty (line 202).
- `test_str_token_expires_within_24h_shows_expired` — __str__ shows 'EXPIRED' when token_expires is set but within 24 hours (line 219->226).
- `test_jwt_payload_needing_base64_padding` — JWT payload segment that needs padding (line 260: payload_b64 += '=' * ...).

**TestWebserviceCredentialsReprCoverage** — Test WebserviceCredentials.__repr__ (line 325/328).

- `test_webservice_credentials_str_and_repr_unreachable` — Confirm that WebserviceCredentials cannot be instantiated to reach __str__/__repr__.

**TestExtractJwtExpiryEdgeCases** — Cover line 258: token with < 2 parts.

- `test_token_no_dots_returns_none`
- `test_token_single_dot_returns_none`

**TestOAuth2StrNoTokenExpires** — Cover branch 219->226: __str__ when token_expires is None.

- `test_str_no_token_expires` — JWT without exp claim → token_expires=None → no expiry info in str.

### `tests/unit/test_data_normalizer.py`

_Unit tests for DataNormalizer - comprehensive coverage of all static methods._


**TestFixZipCode** — Tests for ZIP code leading-zero restoration.

- `test_integer_inputs`
- `test_string_inputs_needing_padding`
- `test_string_with_leading_whitespace`
- `test_none_returns_empty`
- `test_empty_string_returns_empty`
- `test_non_numeric_string_returned_as_is`
- `test_already_five_digit_string`
- `test_negative_integer`
- `test_non_standard_type_converted_to_str`

**TestNormalizeDatetime** — Tests for datetime normalization to SOAP format.

- `test_datetime_object_formatted`
- `test_datetime_object_am_pm`
- `test_string_input_returned_stripped`
- `test_string_input_already_clean`
- `test_none_returns_empty_string`
- `test_non_string_non_datetime_converted`

**TestNormalizeDateString** — Tests for reporting-period date string normalization.

- `test_valid_mm_dd_yyyy_returned`
- `test_strips_whitespace`
- `test_invalid_format_returned_with_warning`
- `test_none_returns_empty`
- `test_non_string_converted`

**TestNormalizeForValidation** — Tests for the combined normalize + stats entry point.

- `test_rest_protocol_normalizes`
- `test_soap_protocol_passthrough`
- `test_empty_data`

**TestValidatePydanticCompatibility** — Tests for Pydantic pre-validation checks.

- `test_panel_missing_id_rssd`
- `test_panel_wrong_type_id_rssd`
- `test_panel_bad_zip_4_digits`
- `test_panel_valid_data`
- `test_filers_since_date_non_string_items`
- `test_filers_since_date_valid`
- `test_missing_name_field`

**TestNormalizeResponse** — Tests for the main normalization entry point.

- `test_panel_of_reporters_full`
- `test_filers_since_date_int_to_str`
- `test_reporting_periods_date_normalization`
- `test_unknown_endpoint_warns_returns_unchanged`
- `test_empty_data_returns_unchanged`
- `test_soap_protocol_returns_unchanged`
- `test_retrieve_facsimile_preserves_binary`
- `test_ubpr_reporting_periods`
- `test_filers_submission_datetime`

**TestApplyNormalizations** — Tests for the internal normalization dispatch.

- `test_list_with_array_items`
- `test_list_of_objects`
- `test_dict_input`
- `test_preserve_binary`
- `test_simple_value_no_coercion`
- `test_simple_value_with_simple_value_coercion`

**TestNormalizeObject** — Tests for per-object field coercion.

- `test_coercion_applied`
- `test_missing_field_skipped`
- `test_coercion_failure_keeps_original`
- `test_meta_fields_skipped`
- `test_non_dict_input_returned_as_is`
- `test_original_not_mutated`
- `test_unchanged_value_not_counted` — If coercion returns same value, no update occurs.

**TestValidateNormalizedData** — Tests for post-normalization validation.

- `test_valid_data_no_warnings`
- `test_invalid_zip_4_digit_warns`
- `test_non_string_id_rssd_warns`
- `test_empty_data_no_error`
- `test_dict_input_validated`
- `test_non_string_zip_warns`
- `test_zip_pattern_mismatch_warns`

**TestGetNormalizationStats** — Tests for normalization statistics.

- `test_counts_transformations`
- `test_type_changes_tracked`
- `test_list_data_comparison`
- `test_value_change_same_type`
- `test_stats_structure`
- `test_validation_passed_flag`

**TestEstimateDataSize** — Tests for data size estimation.

- `test_list_size`
- `test_dict_size`
- `test_none_returns_zero`
- `test_string_size`
- `test_empty_list`

**TestCountObjectChanges** — Tests for per-object change counting.

- `test_type_changes`
- `test_value_changes_same_type`
- `test_unchanged_fields`
- `test_multiple_changes`
- `test_bool_to_str_tracked`
- `test_field_only_in_before_ignored` — If a key in before is absent in after, it is not counted.

**TestNormalizeResponseFailure** — Tests for normalize_response failure path (lines 340-344).

- `test_apply_normalizations_exception_returns_original_data` — If _apply_normalizations raises, should return original data (lines 340-344).

**TestValidateObject4DigitZIP** — Tests for _validate_object with 4-digit ZIP string (lines 471-472).

- `test_4digit_zip_string_produces_error` — A 4-digit numeric string ZIP should produce a 'missing leading zero' error (lines 471-472).

**TestGetNormalizationStatsException** — Tests for get_normalization_stats exception handling (lines 527-529).

- `test_exception_during_comparison_adds_error_key` — Exception during comparison should set error key in stats (lines 527-529).

**TestValidateNormalizedDataErrorAccumulation** — Tests for validation error accumulation (lines 447-448).

- `test_validation_exception_caught` — Exception during validation should be caught and logged (lines 447-448).
- `test_multiple_validation_errors_logged` — Multiple validation issues should be accumulated and logged (line 444-445).

**TestValidatePydanticCompatibilityException** — Tests for exception in validate_pydantic_compatibility (lines 286-288).

- `test_exception_sets_error_and_incompatible` — Exception during validation should set error and compatible=False (lines 286-288).

**TestValidatePydanticBranchPartials** — Tests for branch-partial misses in validate_pydantic_compatibility.

- `test_panel_reporters_dict_not_list_skips_validation` — 246->290: RetrievePanelOfReporters with dict input (not list) skips loop.
- `test_panel_reporters_list_with_non_dict_item` — 248->247: Loop item that is NOT a dict should be skipped.
- `test_filers_since_date_dict_not_list_skips_validation` — 278->290: RetrieveFilersSinceDate with dict input (not list) skips loop.

**TestValidateObjectBranchPartials** — Tests for branch-partial misses in _validate_object.

- `test_zip_non_string_produces_error` — 471->454: ZIP field where value is NOT a string.
- `test_id_rssd_valid_string_passes` — 475->454: ID_RSSD where value IS a string passes validation (no error).
- `test_id_rssd_non_string_produces_error` — 477->454: ID_RSSD where value is NOT a string.

**TestGetNormalizationStatsDictBranch** — Tests for get_normalization_stats dict before/after branch (516->524).

- `test_dict_before_and_after` — 516->524: isinstance(data_before, dict) branch with dict data.

### `tests/unit/test_datahelpers.py`

_Tests for ffiec_data_connect.datahelpers._normalize_output_from_reporter_panel_


**TestIDRSSD**

- `test_id_rssd_present`
- `test_id_rssd_missing`

**TestFDICCertNumber**

- `test_nonzero`
- `test_zero`
- `test_missing`

**TestOCCChartNumber**

- `test_nonzero`
- `test_zero`
- `test_missing`

**TestOTSDockNumber**

- `test_nonzero`
- `test_zero`
- `test_missing`

**TestPrimaryABARoutNumber**

- `test_nonzero`
- `test_zero`

**TestName**

- `test_present_with_value`
- `test_present_with_zero_string`
- `test_missing`

**TestState**

- `test_present`
- `test_missing_sets_state_to_none` — When State is missing, state should be set to None.

**TestCity**

- `test_present`
- `test_missing`

**TestAddress**

- `test_present`

**TestZip**

- `test_integer_zip_padded_to_five`
- `test_string_zip`
- `test_uppercase_ZIP`
- `test_zip_missing`
- `test_zip_preferred_over_ZIP` — When both 'Zip' and 'ZIP' are present, 'Zip' takes precedence.

**TestFilingType**

- `test_present_with_value`

**TestHasFiledForReportingPeriod**

- `test_bool_true`
- `test_bool_false`
- `test_non_bool_becomes_none`
- `test_missing`

**TestStateZeroString** — Test State field with value '0' (line 81).

- `test_state_zero_string`

**TestCityZeroString** — Test City field with value '0' (line 91).

- `test_city_zero_string`

**TestAddressZeroString** — Test Address field with value '0' (line 101).

- `test_address_zero_string`

**TestZipZeroValue** — Test Zip field with value 0 (line 117: zfill produces '00000', not '0').

- `test_zip_integer_zero` — Zip=0 -> str(0).zfill(5) -> '00000', which is NOT '0', so hits else branch.

**TestFilingTypeZeroString** — Test FilingType field with value '0' (line 127).

- `test_filing_type_zero_string`

**TestFieldsEmptyString** — Test fields with empty string values to cover the 'or temp_str == ""' branches.

- `test_state_empty_string`
- `test_city_empty_string`
- `test_address_empty_string`
- `test_filing_type_empty_string`

**TestFullRow** — Integration-style test: pass a complete row resembling a REST API response.

- `test_complete_row`

### `tests/unit/test_documentation_build.py`

_Unit tests for documentation build validation._


**TestDocumentationBuild** — Test documentation build process.

- `test_sphinx_build_html` — Test that Sphinx can build HTML documentation without errors.
- `test_sphinx_build_linkcheck` — Test that external links in documentation are valid.
- `test_rst_syntax_validation` — Test that all RST files have valid syntax.
- `test_documentation_dependencies` — Test that all documentation dependencies are correctly specified.
- `test_conf_py_configuration` — Test that Sphinx configuration is valid.
- `test_rst_linting_with_doc8` — Test RST files with doc8 linter.
- `test_rst_syntax_with_rstcheck` — Test RST files with rstcheck syntax checker.

### `tests/unit/test_dual_field_compatibility.py`

_Unit tests for dual field compatibility ('rssd' and 'id_rssd')._


**TestDualFieldCompatibility** — Test dual field support across all functions that return RSSD data.

- `test_normalize_output_from_reporter_panel_dual_fields` — Test that datahelpers normalization provides both fields.
- `test_normalize_output_missing_id_rssd` — Test normalization when ID_RSSD is missing.
- `test_collect_filers_since_date_dual_fields_polars` — Test collect_filers_since_date provides dual fields in Polars output via enhanced method.
- `test_xbrl_processor_dual_fields` — Test that XBRL processor provides dual fields.
- `test_enhanced_methods_use_same_normalization` — Test that enhanced methods use the same normalization functions as SOAP methods.
- `test_all_functions_provide_consistent_field_names` — Integration test to verify all functions use consistent field naming.

### `tests/unit/test_exceptions_detailed.py`

_Tests for ffiec_data_connect.exceptions — constructor and string behaviour._


**TestFFIECError**

- `test_str_without_details`
- `test_str_with_details`
- `test_is_exception`

**TestNoDataError**

- `test_without_params`
- `test_with_rssd_id`
- `test_with_reporting_period`
- `test_with_both`

**TestCredentialError**

- `test_without_credential_source`
- `test_with_credential_source`

**TestConnectionError**

- `test_without_optional_args`
- `test_with_url`
- `test_with_status_code`
- `test_with_url_and_status_code`

**TestRateLimitError**

- `test_without_retry_after`
- `test_with_retry_after`

**TestXMLParsingError**

- `test_without_snippet`
- `test_with_short_snippet`
- `test_with_long_snippet_truncated`

**TestSessionError**

- `test_without_session_state`
- `test_with_session_state`

**TestSOAPDeprecationError**

- `test_attributes`
- `test_message_contains_soap_method`
- `test_message_contains_rest_equivalent`
- `test_message_contains_code_example`
- `test_details_dict`
- `test_message_mentions_shutdown_date`
- `test_is_ffiec_error`

### `tests/unit/test_ffiec_connection.py`

_Unit tests for ffiec_connection.py after SOAP deprecation._


**TestFFIECConnectionRaisesDeprecation** — All attempts to instantiate FFIECConnection must raise SOAPDeprecationError.

- `test_instantiation_raises_soap_deprecation_error` — FFIECConnection() raises SOAPDeprecationError.
- `test_error_message_mentions_session_none` — The migration guidance tells the user to pass session=None.
- `test_error_message_mentions_oauth2_credentials` — The migration guidance mentions OAuth2Credentials.
- `test_error_attributes` — The raised exception carries structured migration metadata.

**TestImportability** — Verify that the module's public names are still importable.

- `test_ffiec_connection_importable` — FFIECConnection class is importable (isinstance compatibility).
- `test_proxy_protocol_enum_importable` — ProxyProtocol enum is still importable and has expected members.

### `tests/unit/test_legacy_compatibility.py`

_Test legacy error compatibility mode._


**TestLegacyErrorMode** — Test legacy error compatibility.

- `test_legacy_mode_default_enabled` — Test that legacy mode is enabled by default for backward compatibility.
- `test_enable_legacy_mode` — Test enabling legacy mode.
- `test_set_legacy_errors` — Test setting legacy errors flag.
- `test_environment_variable` — Test that environment variable controls default.
- `test_credentials_always_raise_soap_deprecation` — Test that WebserviceCredentials always raises SOAPDeprecationError regardless of legacy mode.
- `test_validation_error_legacy_mode` — Test that validation errors raise ValueError in legacy mode.
- `test_all_error_types_legacy_mode` — Test that all error types work in legacy mode.
- `test_legacy_mode_thread_local` — Test that legacy mode setting is global, not thread-local.
- `test_deprecation_warning_shown` — Test that deprecation warning is shown when using legacy mode.

### `tests/unit/test_memory_leaks.py`

_Comprehensive memory leak detection test suite for FFIEC Data Connect._


**TestCredentialsMemoryLeaks** — Test memory leaks in credentials module.

- `test_webservice_credentials_raises_soap_deprecation` — Test that WebserviceCredentials raises SOAPDeprecationError.
- `test_mock_credential_object_cleanup` — Test that mock credential objects are properly garbage collected.
- `test_mock_credential_memory_after_gc` — Test that mock credentials release memory after garbage collection.

**TestFFIECConnectionMemoryLeaks** — Test memory leaks in FFIEC connection management.

- `test_connection_raises_soap_deprecation` — Test that FFIECConnection raises SOAPDeprecationError.

**TestAsyncCompatibleClientMemoryLeaks** — Test memory leaks in async compatible client.

- `test_client_data_collection_memory` — Test memory usage during data collection operations.
- `test_connection_cache_memory_management` — Test memory management of connection caching.
- `test_rate_limiter_memory_stability` — Test rate limiter memory usage over time.
- `test_client_garbage_collection` — Test that clients are properly garbage collected.
- `test_parallel_processing_memory` — Test memory usage during parallel processing.

**TestMethodsMemoryLeaks** — Test memory leaks in methods module.

- `test_validation_function_memory_stability` — Test memory stability of validation functions.
- `test_date_utility_memory_efficiency` — Test memory efficiency of date utility functions.

**TestIntegrationMemoryLeaks** — Test memory leaks in integration scenarios.

- `test_full_workflow_memory_stability` — Test memory stability during full workflow simulation.
- `test_long_running_session_memory` — Test memory behavior in long-running sessions.
- `test_exception_handling_memory_cleanup` — Test that exceptions don't cause memory leaks.

**TestMemoryPressureScenarios** — Test behavior under memory pressure scenarios.

- `test_high_volume_object_creation` — Test memory behavior with high volume object creation.
- `test_memory_cleanup_under_gc_pressure` — Test memory cleanup behavior when garbage collector is under pressure.

### `tests/unit/test_methods.py`

_Comprehensive unit tests for methods.py with memory leak focus._


**TestDateUtilities** — Test date conversion and validation utilities.

- `test_create_ffiec_date_from_datetime` — Test FFIEC date creation from datetime object.
- `test_convert_any_date_to_ffiec_format` — Test conversion of various date formats to FFIEC format.
- `test_convert_any_date_invalid_format` — Test error handling for invalid date formats.
- `test_convert_quarter_to_date` — Test quarter string conversion to datetime.
- `test_is_valid_date_or_quarter` — Test date and quarter validation.
- `test_return_ffiec_reporting_date` — Test FFIEC reporting date generation.
- `test_return_ffiec_reporting_date_invalid` — Test error handling for invalid reporting dates.

**TestValidators** — Test input validation functions.

- `test_output_type_validator` — Test output type validation.
- `test_date_format_validator` — Test date format validation.
- `test_credentials_validator` — Test credentials validation.
- `test_session_validator` — Test session validation.
- `test_validate_rssd_id` — Test RSSD ID validation and conversion.
- `test_validate_rssd_id_memory_efficiency` — Test RSSD ID validation doesn't leak memory on large inputs.

**TestSOAPDeprecation** — Test that SOAP paths raise SOAPDeprecationError.

- `test_collect_reporting_periods_soap_raises` — Test that SOAP credentials raise SOAPDeprecationError.
- `test_collect_data_soap_raises` — Test that SOAP credentials raise SOAPDeprecationError.
- `test_collect_filers_since_date_soap_raises` — Test that SOAP credentials raise SOAPDeprecationError.
- `test_collect_filers_submission_date_time_soap_raises` — Test that SOAP credentials raise SOAPDeprecationError.
- `test_collect_filers_on_reporting_period_soap_raises` — Test that SOAP credentials raise SOAPDeprecationError.
- `test_deprecation_error_contains_migration_info` — Test that SOAPDeprecationError contains helpful migration info.
- `test_deprecation_error_contains_portal_url` — Test that SOAPDeprecationError contains the FFIEC portal URL.

**TestConcurrentAccess** — Test thread safety and concurrent access patterns.

- `test_date_utilities_thread_safety` — Test that date utilities are thread-safe.
- `test_validators_thread_safety` — Test that validators are thread-safe.

**TestMethodsCoverage** — Additional tests for full coverage of methods.py.

- `test_convert_quarter_to_date_invalid_quarter_number` — _convert_quarter_to_date with quarter number 5 returns None (lines 133-137).
- `test_return_ffiec_reporting_date_malformed_quarter` — _return_ffiec_reporting_date with '5Q2023' raises ValueError (line 188).
- `test_return_ffiec_reporting_date_unconvertible_string` — _return_ffiec_reporting_date with non-parseable string raises ValueError (line 195).
- `test_collect_data_invalid_force_null_types` — collect_data with force_null_types='invalid' raises ValidationError (line 480).
- `test_collect_data_rest_polars_output` — collect_data REST path with output_type='polars' processes XBRL data.
- `test_collect_data_rest_list_output` — collect_data REST path with output_type='list' returns list.

**TestUBPRMethodsCoverage** — Tests for collect_ubpr_facsimile_data coverage.

- `test_collect_ubpr_facsimile_list_output` — collect_ubpr_facsimile_data with output_type='list' returns processed list.
- `test_collect_ubpr_facsimile_pandas_output` — collect_ubpr_facsimile_data with output_type='pandas' returns DataFrame.
- `test_collect_ubpr_facsimile_force_numpy_nulls` — collect_ubpr_facsimile_data with force_null_types='numpy'.
- `test_collect_ubpr_facsimile_force_pandas_nulls` — collect_ubpr_facsimile_data with force_null_types='pandas'.
- `test_collect_ubpr_facsimile_non_bytes_raw_data` — collect_ubpr_facsimile_data with non-bytes raw_data returns as-is.

**TestPolarsImportFallback** — Test polars import fallback path (lines 23-25).

- `test_polars_import_failure_sets_flag_false` — When polars import fails, POLARS_AVAILABLE should be False and pl None.

**TestReturnFfiecReportingDateBranches** — Cover remaining branches in _return_ffiec_reporting_date (lines 184-213).

- `test_valid_quarter_maps_correctly` — A valid quarter string like '1Q2023' returns correct FFIEC date (line 184->exit via quarter).
- `test_yyyymmdd_string_quarter_end` — YYYYMMDD string for a quarter end returns FFIEC date (line 205).
- `test_yyyy_mm_dd_string_quarter_end_june` — YYYY-MM-DD string for June 30 returns FFIEC date (line 209).
- `test_mm_dd_yyyy_string_quarter_end_september` — MM/DD/YYYY string for September 30 returns FFIEC date (line 213).
- `test_mm_dd_yyyy_string_not_quarter_end_raises` — MM/DD/YYYY string that is NOT a quarter end raises ValueError (line 195).
- `test_yyyymmdd_non_quarter_end_raises` — YYYYMMDD string for a non-quarter end raises ValueError.
- `test_yyyy_mm_dd_non_quarter_end_raises` — YYYY-MM-DD string for a non-quarter end raises ValueError.

**TestConvertQuarterToDateNoneBranch** — Cover line 133: _convert_quarter_to_date returns None for impossible quarter.

- `test_invalid_format_returns_none` — Non-matching format returns None from else branch.
- `test_non_quarter_string_returns_none` — Non-quarter string returns None.

**TestCollectDataRESTBranches** — Cover REST path branches in collect_data (lines 515-518, 529, 531, 618, 622-627).

- `test_rest_adapter_returns_non_bytes_non_str_raises` — When adapter returns non-bytes/non-str (e.g. int), raise ValidationError (lines 515-518).
- `test_rest_adapter_returns_string_xml` — When adapter returns a string (not bytes), it should be encoded and processed (lines 529, 531).
- `test_rest_adapter_returns_string_force_numpy_nulls` — String data with force_null_types='numpy' uses numpy nulls (line 529).
- `test_rest_adapter_returns_string_force_pandas_nulls` — String data with force_null_types='pandas' uses pandas nulls (line 531).
- `test_rest_connection_error_server_error_500` — ConnectionError with 'server error 500' triggers logging and re-raise (lines 618, 622-627).
- `test_rest_connection_error_generic` — ConnectionError without 'server error' or '500' still re-raises (line 627).
- `test_rest_default_output_returns_normalized_data` — When output_type is not list/pandas/polars, return normalized_data (line 618).

**TestCollectFilersOAuth2Delegation** — Cover OAuth2 delegation paths for collect_filers_* and collect_filers_submission_date_time (lines 760-762, 839-841).

- `test_collect_filers_submission_date_time_oauth2` — collect_filers_submission_date_time with OAuth2 delegates to enhanced (lines 760-762).
- `test_collect_filers_on_reporting_period_oauth2` — collect_filers_on_reporting_period with OAuth2 delegates to enhanced (lines 839-841).

**TestCollectUBPRReportingPeriodsCoverage** — Cover collect_ubpr_reporting_periods lines 883-903.

- `test_ubpr_reporting_periods_list_output` — collect_ubpr_reporting_periods with output_type='list' returns sorted list (line 903).
- `test_ubpr_reporting_periods_pandas_output` — collect_ubpr_reporting_periods with output_type='pandas' returns DataFrame (line 901).
- `test_ubpr_reporting_periods_soap_raises` — collect_ubpr_reporting_periods with SOAP creds raises SOAPDeprecationError.

**TestCollectUBPRFacsimileDataCoverage** — Cover remaining lines in collect_ubpr_facsimile_data (lines 952, 962, 979, 983, 995, 1019-1046).

- `test_invalid_force_null_types_raises` — force_null_types='invalid' raises ValidationError (line 952).
- `test_invalid_reporting_period_raises` — Invalid reporting period raises ValidationError (line 962).
- `test_datetime_reporting_period` — Datetime reporting_period converts correctly (line 979).
- `test_unconvertible_string_reporting_period_raises` — String reporting period that can't convert raises ValidationError (line 983).
- `test_bytes_output_returns_raw_data` — output_type='bytes' returns raw data directly (line 995).
- `test_non_bytes_raw_data_with_bytes_output` — Non-bytes raw_data with output_type='bytes' returns raw data (line 995).
- `test_pandas_output_with_force_numpy_nulls` — Pandas output with force_null_types='numpy' covers lines 1034-1038.
- `test_pandas_output_with_force_pandas_nulls` — Pandas output with force_null_types='pandas' covers lines 1019-1032, 1041-1044.
- `test_non_bytes_raw_data_with_pandas_output` — Non-bytes raw_data with output_type='pandas' returns raw_data as-is (line 1046/1048).
- `test_soap_creds_raises` — SOAP credentials raise SOAPDeprecationError.

**TestReturnFfiecReportingDateLine195** — Cover line 195: unconvertible date string that is not a quarter.

- `test_non_date_non_quarter_string` — A string where index [1] != 'Q' and no regex matches → ValueError.
- `test_non_quarter_end_date` — A valid date format that is not a quarter end → ValueError.

**TestCollectUBPRFacsimilePandasBranches** — Cover UBPR pandas branch partials: columns present/absent.

- `test_ubpr_pandas_with_missing_columns` — UBPR XBRL with only some columns exercises all if-column-in-df branches.
- `test_ubpr_non_bytes_pandas_passthrough` — Non-bytes raw_data with pandas output_type returns raw_data (line 1046).
- `test_ubpr_bytes_unexpected_output_type` — Bytes raw_data with unexpected output_type returns raw_data (line 1044).

**TestReturnFfiecReportingDateNonStringNonDatetime** — Cover branch 182->exit: input that is neither str nor datetime.

- `test_integer_input_returns_none` — Non-str, non-datetime input falls through without returning.

### `tests/unit/test_methods_enhanced.py`

_Unit tests for methods_enhanced.py_


**TestCollectReportingPeriodsEnhanced** — Tests for collect_reporting_periods_enhanced.

- `test_returns_sorted_ascending_list` — Periods should be sorted oldest-first regardless of API order.
- `test_returns_pandas_dataframe` — output_type='pandas' should return a DataFrame with reporting_period column.
- `test_ubpr_series_calls_ubpr_endpoint` — series='ubpr' should call retrieve_ubpr_reporting_periods.
- `test_date_output_format_string_original` — string_original format should pass through dates unchanged.
- `test_date_output_format_other` — Non-default date_output_format should still return data (format passthrough).
- `test_single_period_no_sort_needed` — Single period should be returned as-is.

**TestCollectFilersOnReportingPeriodEnhanced** — Tests for collect_filers_on_reporting_period_enhanced.

- `test_returns_normalized_list_with_dual_field_names` — Pydantic-like filer objects should be normalized with both rssd and id_rssd.
- `test_pydantic_model_normalization` — Pydantic-like objects with model_dump() should be normalized.
- `test_returns_pandas_dataframe` — output_type='pandas' should return a DataFrame.
- `test_datetime_reporting_period` — Should accept a datetime object as reporting_period.

**TestCollectFilersSinceDateEnhanced** — Tests for collect_filers_since_date_enhanced.

- `test_returns_string_rssd_ids` — Returned RSSD IDs should be strings.
- `test_integer_rssd_ids_converted_to_strings` — Integer RSSD IDs from adapter should be converted to strings.
- `test_pandas_output_has_dual_columns` — Pandas output should have both rssd_id and rssd columns.
- `test_empty_list` — Empty result from adapter should return empty list.

**TestCollectFilersSubmissionDateTimeEnhanced** — Tests for collect_filers_submission_date_time_enhanced.

- `test_dict_submissions_dual_field_names` — Dict submissions should produce both rssd and id_rssd fields.
- `test_pydantic_submissions_dual_field_names` — Pydantic-like submission objects should be processed correctly.
- `test_pandas_output` — output_type='pandas' should return a DataFrame.
- `test_date_output_format_passthrough` — date_output_format should not alter the datetime string (current behavior).

**TestNormalizePydanticToSoapFormat** — Tests for _normalize_pydantic_to_soap_format helper.

- `test_with_pydantic_model_having_model_dump` — Pydantic models (with model_dump) should be normalized via datahelpers.
- `test_with_plain_dict` — Plain dicts without model_dump should be normalized directly.
- `test_missing_rssd_returns_none` — Dict without ID_RSSD should set rssd/id_rssd to None.

**TestFormatDatetimeForOutput** — Tests for _format_datetime_for_output helper.

- `test_string_original_returns_as_is` — string_original format should return the datetime string unchanged.
- `test_other_format_returns_as_is` — Non-string_original formats also pass through (current implementation).
- `test_empty_string_returns_empty` — Empty string should be returned as-is (falsy check).
- `test_none_returns_none` — None should be returned as-is (falsy check).

**TestCollectReportingPeriodsEnhancedExtended** — Additional tests for collect_reporting_periods_enhanced coverage.

- `test_invalid_series_hits_validation_branch` — Invalid series should trigger the validation branch (line 123).
- `test_exception_from_adapter_hits_error_handler` — Exception from adapter should reach the except block (lines 170-172).

**TestCollectReportingPeriodsEnhancedPolars** — Test polars output for collect_reporting_periods_enhanced (line 166).

- `test_polars_output_type` — output_type='polars' should return a polars DataFrame (line 166).

**TestCollectFilersOnReportingPeriodEnhancedValidation** — Tests for validation paths in collect_filers_on_reporting_period_enhanced.

- `test_invalid_reporting_period_raises_validation_error` — Invalid reporting_period should raise ValidationError (line 208).
- `test_unconvertible_period_raises_validation_error` — Period that passes validation but fails conversion should raise (line 223).

**TestCollectFilersOnReportingPeriodEnhancedExtended** — Additional tests for collect_filers_on_reporting_period_enhanced coverage.

- `test_polars_output_type` — output_type='polars' should return a polars DataFrame (lines 248-249).

**TestCollectFilersSinceDateEnhancedExtended** — Additional tests for collect_filers_since_date_enhanced coverage.

- `test_invalid_reporting_period_raises_validation_error` — Invalid reporting_period should raise ValidationError (line 208).
- `test_invalid_since_date_raises_validation_error` — Invalid since_date should raise ValidationError (line 223).
- `test_polars_output_type` — output_type='polars' should return a polars DataFrame (lines 250, 254-258).

**TestCollectFilersSubmissionDateTimeEnhancedExtended** — Additional tests for collect_filers_submission_date_time_enhanced coverage.

- `test_invalid_reporting_period_raises_validation_error` — Invalid reporting_period should raise ValidationError (lines 289, 394).
- `test_invalid_since_date_raises_validation_error` — Invalid since_date should raise ValidationError (lines 299, 403).
- `test_datetime_inputs_converted` — datetime objects should be converted via _create_ffiec_date_from_datetime (lines 311, 415).
- `test_polars_output_type` — output_type='polars' should return a polars DataFrame (lines 351-352, 356-358).
- `test_exception_from_adapter_hits_error_handler` — Exception from adapter should reach the except block (lines 474-481).

**TestPolarsImportFallbackEnhanced** — Test polars import fallback path (lines 37-39).

- `test_polars_import_failure_sets_flag_false` — When polars import fails, POLARS_AVAILABLE should be False and pl None.

**TestSchemaValidationWarning** — Test that schema validation warnings are logged (line 146).

- `test_incompatible_schema_logs_warning` — When validate_pydantic_compatibility returns compatible=False, logger.warning fires (line 146).

**TestCollectFilersOnReportingPeriodEnhancedExceptBlock** — Cover the except block in collect_filers_on_reporting_period_enhanced (lines 253-257).

- `test_adapter_exception_hits_except_block` — Exception from adapter triggers the except block (lines 253-257).

**TestCollectFilersSinceDateEnhancedDatetimeInputs** — Cover datetime conversion in collect_filers_since_date_enhanced (lines 310, 315, 320).

- `test_datetime_reporting_period_and_since_date` — datetime objects for both reporting_period and since_date (lines 310, 315).
- `test_none_date_conversion_raises_validation_error` — When date conversion returns None, ValidationError is raised (line 320).

**TestCollectFilersSinceDateEnhancedExceptBlock** — Cover the except block in collect_filers_since_date_enhanced (lines 353-355).

- `test_adapter_exception_hits_except_block` — Exception from adapter triggers the except block (lines 353-355).

**TestCollectFilersSubmissionDateTimeEnhancedDatetimeInputs** — Cover datetime conversion in collect_filers_submission_date_time_enhanced (lines 412, 417, 422).

- `test_datetime_reporting_period_and_since_date_happy_path` — datetime objects for both reporting_period and since_date succeed (lines 412, 417).
- `test_none_date_conversion_raises_validation_error` — When date conversion returns None, ValidationError is raised (line 422).

### `tests/unit/test_numpy_dtypes.py`

_Test numpy dtype handling throughout XBRL → pandas → polars pipeline._


**TestNumpyDtypeFlow** — Test numpy dtype consistency throughout data pipeline.

- `test_xbrl_processor_returns_numpy_types` — Test that XBRL processor returns proper numpy types.
- `test_pandas_dataframe_preserves_numpy_dtypes` — Test that pandas DataFrame creation preserves numpy dtypes.
- `test_polars_conversion_maintains_types` — Test that polars conversion maintains numpy dtypes.
- `test_end_to_end_dtype_pipeline` — Test complete pipeline: XBRL → pandas → polars maintains dtypes.

### `tests/unit/test_oauth2_credentials.py`

_Unit tests for OAuth2Credentials class._


**TestOAuth2CredentialsInitialization** — Test OAuth2 credential initialization scenarios.

- `test_init_with_explicit_credentials` — Test initialization with explicit OAuth2 credentials.
- `test_init_with_expired_token` — Test initialization with expired token shows warning.
- `test_init_with_invalid_token_format` — Test that invalid JWT format raises error.
- `test_init_missing_username` — Test that missing username raises error.
- `test_init_missing_bearer_token` — Test that missing bearer token raises error.
- `test_token_validation_valid_format` — Test JWT token format validation for valid tokens.
- `test_token_validation_invalid_format` — Test JWT token format validation for invalid tokens.

**TestOAuth2CredentialsSecurity** — Test security aspects of OAuth2 credential handling.

- `test_token_masking_in_str` — Test that bearer tokens are masked in string representation.
- `test_token_masking_in_repr` — Test that bearer tokens are masked in repr.

**TestOAuth2CredentialsExpiration** — Test OAuth2 credential expiration handling.

- `test_token_not_expired` — Test token that is not expired.
- `test_token_expired` — Test token that is expired.
- `test_token_expiring_soon` — Test token expiring within warning threshold.
- `test_token_expiration_calculation` — Test token expiration time calculation.
- `test_token_expired_calculation` — Test expired token detection.

**TestOAuth2CredentialsComparison** — Test OAuth2 credential comparison with WebserviceCredentials.

- `test_oauth2_vs_webservice_detection` — Test that OAuth2 and Webservice credentials can be distinguished.

### `tests/unit/test_polars_direct_conversion.py`

_Test direct XBRL to polars conversion to ensure maximum type precision._


**TestPolarsDirectConversion** — Test direct XBRL → polars conversion functionality.

- `test_polars_output_type_validation` — Test that polars is accepted as a valid output type.
- `test_polars_unavailable_error` — Test proper error when polars is not available.
- `test_direct_polars_conversion_preserves_types` — Test that direct polars conversion preserves data types.
- `test_empty_data_returns_correct_schema` — Test that empty data returns polars DataFrame with correct schema.
- `test_numpy_nan_handling_in_polars` — Test that numpy NaN values are properly converted to polars nulls.

### `tests/unit/test_protocol_adapter_v3.py`

_Unit tests for protocol_adapter.py_


**TestRESTAdapterHandleResponse** — Tests for RESTAdapter._handle_response status code handling.

- `test_200_returns_json` — HTTP 200 should parse and return JSON body.
- `test_200_invalid_json_raises_ffiec_error` — HTTP 200 with unparseable body should raise FFIECError.
- `test_204_returns_empty_list` — HTTP 204 (No Content) should return an empty list.
- `test_400_raises_validation_error` — HTTP 400 should raise ValidationError.
- `test_401_raises_credential_error` — HTTP 401 should raise CredentialError.
- `test_403_raises_credential_error` — HTTP 403 should raise CredentialError with detailed message.
- `test_404_raises_no_data_error` — HTTP 404 should raise NoDataError.
- `test_429_raises_rate_limit_error` — HTTP 429 should raise RateLimitError.
- `test_429_with_non_numeric_retry_after` — HTTP 429 with non-numeric Retry-After defaults to 60 seconds.
- `test_429_without_retry_after_header` — HTTP 429 without Retry-After header defaults to 60 seconds.
- `test_500_raises_connection_error` — HTTP 500 should raise ConnectionError.
- `test_unexpected_status_raises_ffiec_error` — Unexpected status codes should raise FFIECError.

**TestRESTAdapterValidateResponse** — Tests for RESTAdapter._validate_response Pydantic validation wrapper.

- `test_root_model_unwraps_root` — Models with a root attribute should return root data.
- `test_nested_root_models_unwrapped` — Nested RootModels should be flattened: each item.root extracted.
- `test_regular_model_returned_as_is` — Models without root attribute should be returned as the validated instance.
- `test_pydantic_validation_error_raises_validation_error` — Pydantic ValidationError should be caught and re-raised as our ValidationError.

**TestRESTAdapterProperties** — Tests for RESTAdapter property and helper methods.

- `test_protocol_name_is_rest` — protocol_name should return 'REST'.
- `test_is_rest_returns_true` — is_rest() should return True.

**TestRateLimiterInit** — Tests for RateLimiter initialization.

- `test_default_parameters` — Default init should set 2500 calls/hour and 0.69 calls/sec.
- `test_custom_parameters` — Custom parameters should override defaults.

**TestRateLimiterWaitIfNeeded** — Tests for RateLimiter.wait_if_needed timing logic.

- `test_sleeps_when_under_interval` — Should sleep when the time since last call is less than min_interval.
- `test_no_sleep_when_enough_time_passed` — Should not sleep when enough time has passed since last call.
- `test_records_call_in_history` — Each call to wait_if_needed should add a timestamp to call_history.
- `test_cleans_old_calls` — Calls older than 1 hour should be cleaned from history.

**TestRateLimiterGetStats** — Tests for RateLimiter.get_stats.

- `test_stats_structure` — get_stats should return a dict with expected keys.
- `test_initial_stats_values` — Initial stats should show zero calls and full quota.
- `test_stats_after_calls` — Stats should reflect calls made.

**TestCreateProtocolAdapter** — Tests for the create_protocol_adapter factory function.

- `test_oauth2_credentials_returns_rest_adapter` — OAuth2Credentials should produce a RESTAdapter.
- `test_webservice_credentials_raises_soap_deprecation` — WebserviceCredentials should raise SOAPDeprecationError.
- `test_invalid_credential_type_raises_credential_error` — Unsupported credential types should raise CredentialError.
- `test_session_passed_to_rest_adapter` — Session parameter should be accepted (even if ignored for REST).

**TestSOAPAdapter** — Tests for the deprecated SOAPAdapter stub.

- `test_init_raises_soap_deprecation_error` — SOAPAdapter instantiation should always raise SOAPDeprecationError.
- `test_init_with_args_raises_soap_deprecation_error` — SOAPAdapter instantiation with any args should raise SOAPDeprecationError.
- `test_error_message_contains_migration_info` — SOAPDeprecationError should contain migration guidance.

**TestRESTAdapterInitCredentialCheck** — Tests for RESTAdapter.__init__ rejecting non-OAuth2 credentials.

- `test_non_oauth2_credentials_raises_credential_error` — Passing non-OAuth2Credentials to RESTAdapter raises CredentialError (line 201).

**TestRESTAdapterMakeRequest** — Tests for RESTAdapter._make_request method body.

- `test_make_request_with_params_and_additional_headers` — _make_request passes params and additional_headers to the request (lines 262, 266).

**TestRESTAdapterRetrieveReportingPeriods** — Tests for RESTAdapter.retrieve_reporting_periods body.

- `test_retrieve_reporting_periods_call` — retrieve_reporting_periods normalizes and validates response (lines 448-467).
- `test_retrieve_reporting_periods_ubpr` — retrieve_reporting_periods with UBPR series uses UBPR validation (lines 457-462).

**TestRESTAdapterRetrieveFacsimile** — Tests for RESTAdapter.retrieve_facsimile JSON+base64 decoding.

- `test_facsimile_json_base64_string` — JSON response with base64-encoded string is decoded (lines 527-535).
- `test_facsimile_json_non_string_returns_content` — JSON response with non-string value returns response.content (lines 536-540).
- `test_facsimile_404_raises_no_data_error` — 404 response raises NoDataError (lines 549-552).
- `test_facsimile_500_raises_connection_error` — 500 response raises ConnectionError (lines 553-562).
- `test_facsimile_unexpected_status_raises_connection_error` — Unexpected status code raises ConnectionError (lines 563-568).

**TestRESTAdapterRetrievePanelOfReporters** — Tests for RESTAdapter.retrieve_panel_of_reporters body.

- `test_retrieve_panel_of_reporters` — retrieve_panel_of_reporters normalizes and validates response (lines 597-609).

**TestRESTAdapterRetrieveFilersSinceDate** — Tests for RESTAdapter.retrieve_filers_since_date body.

- `test_retrieve_filers_since_date` — retrieve_filers_since_date normalizes and validates response (lines 641-653).

**TestRESTAdapterRetrieveUBPRReportingPeriods** — Tests for RESTAdapter.retrieve_ubpr_reporting_periods body.

- `test_retrieve_ubpr_reporting_periods` — retrieve_ubpr_reporting_periods normalizes and validates (lines 740-752).

**TestRESTAdapterRetrieveUBPRXBRLFacsimile** — Tests for RESTAdapter.retrieve_ubpr_xbrl_facsimile JSON/base64 path.

- `test_ubpr_facsimile_json_base64_string` — JSON response with base64-encoded XBRL is decoded (lines 800-811).
- `test_ubpr_facsimile_json_non_string_returns_content` — JSON response with non-string value returns response.content (lines 812-816).
- `test_ubpr_facsimile_404_raises_no_data_error` — 404 response raises NoDataError (lines 825-828).
- `test_ubpr_facsimile_unexpected_status_raises_error` — Unexpected status raises ConnectionError (lines 829-834).

**TestRateLimiterHourlyLimitPreFilled** — Tests for RateLimiter hourly limit branch with pre-filled call history.

- `test_hourly_limit_triggers_sleep_with_full_history` — When call_history has 2500 entries within the last hour, sleep is called (line 915).

**TestRESTAdapterInitExpiredToken** — Tests for RESTAdapter initialization with expired credentials.

- `test_expired_token_logs_warning` — RESTAdapter with expired token should log a warning on init.

**TestRESTAdapterMakeRequestErrors** — Tests for _make_request error handling branches.

- `test_timeout_raises_connection_error` — httpx.TimeoutException should be caught and raised as ConnectionError.
- `test_connect_error_raises_connection_error` — httpx.ConnectError should be caught and raised as ConnectionError.
- `test_request_error_raises_ffiec_error` — httpx.RequestError should be caught and raised as FFIECError.
- `test_expired_token_raises_credential_error` — _make_request with expired credentials should raise CredentialError.

**TestHandleResponse403Expired** — Tests for _handle_response 403 with token expiration details.

- `test_403_with_expired_token_includes_expired_message` — HTTP 403 with expired token should include 'expired' in the error.

**TestHandleResponseDebugLogging** — Tests for debug logging of error response body.

- `test_error_response_body_logged` — Error responses should log the response body in debug.

**TestRetrieveReportingPeriodsException** — Tests for retrieve_reporting_periods exception re-raise.

- `test_exception_is_reraised` — Exceptions in retrieve_reporting_periods should be logged and re-raised.

**TestRetrieveFacsimileUBPR** — Tests for retrieve_facsimile routing to UBPR method.

- `test_ubpr_series_routes_to_ubpr_method` — series='ubpr' should delegate to retrieve_ubpr_xbrl_facsimile.

**TestRetrieveFacsimileResponses** — Tests for retrieve_facsimile response handling branches.

- `test_json_base64_response_decoded` — JSON response with base64 string should be decoded to bytes.
- `test_json_non_string_response_returns_content` — JSON response that is not a string should return raw content.
- `test_non_json_response_returns_content` — Non-JSON response should return raw bytes.
- `test_json_base64_decode_failure_returns_content` — If base64 decode fails, should return raw content.

**TestRetrievePanelOfReportersException** — Tests for retrieve_panel_of_reporters exception re-raise.

- `test_exception_is_reraised` — Exceptions should be logged and re-raised.

**TestRetrieveFilersSinceDateException** — Tests for retrieve_filers_since_date exception re-raise.

- `test_exception_is_reraised` — Exceptions should be logged and re-raised.

**TestRetrieveFilersSubmissionDatetimeNoSinceDate** — Tests for retrieve_filers_submission_datetime with since_date=None.

- `test_q1_period_defaults_to_quarter_start` — Reporting period 03/31/2023 should default lastUpdateDateTime to 01/01/2023.
- `test_q2_period_defaults_to_quarter_start` — Reporting period 06/30/2023 should default lastUpdateDateTime to 04/01/2023.
- `test_q3_period_defaults_to_quarter_start` — Reporting period 09/30/2023 should default lastUpdateDateTime to 07/01/2023.
- `test_q4_period_defaults_to_quarter_start` — Reporting period 12/31/2023 should default lastUpdateDateTime to 10/01/2023.
- `test_malformed_period_defaults_to_fallback` — A malformed reporting_period should use fallback date.

**TestRetrieveFilersSubmissionDatetimeException** — Tests for retrieve_filers_submission_datetime exception re-raise.

- `test_exception_is_reraised` — Exceptions should be logged and re-raised.

**TestRetrieveUBPRReportingPeriodsException** — Tests for retrieve_ubpr_reporting_periods exception re-raise.

- `test_exception_is_reraised` — Exceptions should be logged and re-raised.

**TestRetrieveUBPRFacsimileResponses** — Tests for retrieve_ubpr_xbrl_facsimile response handling.

- `test_json_base64_response_decoded` — JSON response with base64 string should be decoded to bytes.
- `test_json_non_string_response_returns_content` — JSON response that is not a string should return raw content.
- `test_non_json_response_returns_content` — Non-JSON response should return raw bytes.
- `test_json_decode_failure_returns_content` — If JSON/base64 decode fails, should return raw content.

**TestRateLimiterHourlyLimit** — Tests for RateLimiter hourly limit enforcement.

- `test_hourly_limit_causes_sleep` — When hourly limit is reached, should sleep until oldest call ages out.

**TestHandleResponse403NoTokenExpires** — Cover branch 342->348: 403 response when token_expires is None.

- `test_403_without_token_expires` — 403 when credentials have no token_expires should not include expiry message.

**TestRateLimiterHourlyNoWaitNeeded** — Cover branch 915->923: hourly limit reached but oldest call is old enough.

- `test_hourly_limit_no_wait` — When 2500 calls exist but oldest is >1 hour ago, wait_time <= 0.

**TestXBRLRowSkipNone** — Cover xbrl_processor branch 119->118: empty row skipped.

- `test_empty_row_in_items` — XBRL item that processes to None/empty should be skipped.

### `tests/unit/test_reporting_periods_sorting.py`

_Test suite for reporting periods sorting functionality._


**TestReportingPeriodsSorting** — Test suite for the reporting periods sorting functionality.

- `test_sort_soap_format_descending_to_ascending` — Test sorting SOAP format dates from descending to ascending order.
- `test_sort_rest_format_descending_to_ascending` — Test sorting REST format dates from descending to ascending order.
- `test_sort_soap_format_already_ascending` — Test sorting SOAP format dates that are already in ascending order.
- `test_sort_rest_format_already_ascending` — Test sorting REST format dates that are already in ascending order.
- `test_sort_with_single_date_soap` — Test sorting with a single SOAP format date.
- `test_sort_with_single_date_rest` — Test sorting with a single REST format date.
- `test_sort_empty_list` — Test sorting with empty list.
- `test_sort_mixed_years_soap_format` — Test sorting SOAP dates across multiple years.
- `test_sort_mixed_years_rest_format` — Test sorting REST dates across multiple years.
- `test_sort_invalid_format_returns_original` — Test that invalid date formats return the original list unsorted.
- `test_sort_mixed_formats_returns_original` — Test that mixed date formats return the original list unsorted.
- `test_chronological_order_verification_soap` — Verify that sorted SOAP dates are in proper chronological order.
- `test_chronological_order_verification_rest` — Verify that sorted REST dates are in proper chronological order.

**TestCollectReportingPeriodsIntegration** — Integration tests for collect_reporting_periods with sorting.

- `test_rest_api_path_uses_sorting` — Test that REST API path also applies sorting.

### `tests/unit/test_soap_cache.py`

_Tests for deprecated SOAP cache stubs._


**TestSoapCacheStubs** — Test deprecated SOAP cache stub functions.

- `test_clear_soap_cache_emits_deprecation_warning`
- `test_get_cache_stats_emits_deprecation_warning`
- `test_get_cache_stats_returns_expected_dict`
- `test_old_imports_raise_import_error`

### `tests/unit/test_utils.py`

_Unit tests for utils.py coverage._


**TestSortReportingPeriodsCoverage** — Tests targeting uncovered lines in utils.py.

- `test_unparseable_date_in_list_returns_original` — sort_reporting_periods_ascending with unparseable date logs error and returns original list (line 62).
- `test_unparseable_date_logs_error` — sort_reporting_periods_ascending logs an error for unparseable dates.
- `test_inconsistent_format_in_rest_dates` — sort_reporting_periods_ascending with inconsistent REST format returns original.
- `test_empty_list` — sort_reporting_periods_ascending with empty list returns empty list.
- `test_single_item` — sort_reporting_periods_ascending with single item returns same list.
- `test_unknown_format_returns_unsorted` — sort_reporting_periods_ascending with unknown format returns original.

### `tests/unit/test_xbrl_processor.py`

_Unit tests for xbrl_processor.py coverage._


**TestXBRLProcessorCoverage** — Tests targeting uncovered lines in xbrl_processor.py.

- `test_process_xml_empty_bytes_raises_xml_parsing_error` — _process_xml with empty bytes b'' raises XMLParsingError (line 59).
- `test_xbrl_item_without_context_ref_skipped` — XBRL items without @contextRef are skipped (line 185).
- `test_xbrl_item_without_valid_date_in_context_skipped` — XBRL items without a valid date in context are skipped (line 192).
- `test_date_format_string_yyyymmdd` — Date format 'string_yyyymmdd' produces YYYYMMDD output (line 200).
- `test_date_format_python_format` — Date format 'python_format' produces datetime object (line 203).
- `test_date_format_string_original` — Date format 'string_original' produces MM/DD/YYYY output.
- `test_process_xbrl_item_list_input` — _process_xbrl_item handles list of items.
- `test_process_xml_full_pipeline` — Full _process_xml pipeline with real XBRL data.

**TestXBRLProcessorAdditionalCoverage** — Additional tests for uncovered lines in xbrl_processor.py.

- `test_unicode_decode_error_fallback` — Bytes not valid UTF-8 trigger UnicodeDecodeError fallback (line 89).
- `test_date_format_string_yyyymmdd_via_process_xml` — Full pipeline with string_yyyymmdd date format (lines 200-201 via _process_xml).
- `test_value_type_non_monetary_float` — NON-MONETARY unitRef produces float data_type (lines 213-215).
- `test_value_type_bool_true` — value='true' produces bool data_type (lines 216-218).
- `test_value_type_bool_false` — value='false' produces bool data_type (lines 219-221).
- `test_value_type_str_fallback` — Unknown unit type with non-boolean value produces str data_type (lines 222-223).
- `test_value_type_str_when_no_text` — None value with unknown unit produces str data_type (line 223).
- `test_full_pipeline_all_types` — Full pipeline with all value types through _process_xml.

**TestXBRLProcessorOuterUnicodeDecodeError** — Cover line 89: outer UnicodeDecodeError where both parse paths fail.

- `test_corrupt_bytes_raises_xml_parsing_error` — Bytes that can't be decoded as UTF-8, and xmltodict also fails.

### `tests/unit/test_xml_processing_optimizations.py`

_Test XML processing optimizations for memory efficiency._


**TestXMLProcessingOptimizations** — Test XML processing memory optimizations.

- `test_xml_parsing_from_bytes_directly` — Test that XML parsing tries bytes first for memory efficiency.
- `test_xml_parsing_fallback_to_string` — Test fallback to string decoding if bytes parsing fails.
- `test_efficient_dict_construction` — Test that dictionary construction is efficient with single operation.
- `test_generator_expression_usage` — Test that generator expressions are used instead of lists for memory efficiency.
- `test_empty_or_none_item_handling` — Test that empty or None items are handled efficiently.
- `test_error_snippet_memory_efficiency` — Test that error snippets are created efficiently.

**TestDataTypeHandling** — Test optimized data type handling.

- `test_all_data_types_handled_correctly` — Test that all data types are handled with optimized dict construction.

### `tests/integration/test_rest_api_live.py`

_Live integration tests for the FFIEC REST API._


**TestCollectReportingPeriods** — Test collect_reporting_periods against the live API.

- `test_call_series_list`
- `test_call_series_sorted_ascending`
- `test_call_series_pandas`
- `test_ubpr_series`
- `test_date_format_yyyymmdd`
- `test_date_format_python`

**TestCollectData** — Test collect_data (RetrieveFacsimile) against the live API.

- `test_call_series_list`
- `test_call_series_pandas`
- `test_force_null_pandas`
- `test_force_null_numpy`
- `test_various_date_formats` — Multiple date input formats should work.
- `test_datetime_input`

**TestCollectFilersOnReportingPeriod** — Test collect_filers_on_reporting_period (PanelOfReporters).

- `test_list_output`
- `test_pandas_output`
- `test_zip_codes_are_strings` — ZIP codes should be strings (5-digit or ZIP+4).

**TestCollectFilersSinceDate** — Test collect_filers_since_date (FilersSinceDate).

- `test_list_output`
- `test_pandas_output`

**TestCollectFilersSubmissionDateTime** — Test collect_filers_submission_date_time.

- `test_list_output`
- `test_pandas_output`

**TestCollectUBPRReportingPeriods** — Test collect_ubpr_reporting_periods (REST-only endpoint).

- `test_list_output`
- `test_pandas_output`

**TestCollectUBPRFacsimileData** — Test collect_ubpr_facsimile_data (REST-only endpoint).

- `test_list_output`
- `test_pandas_output`

**TestSOAPDeprecationLive** — Verify SOAP classes raise even when credentials are available.

- `test_session_not_none_still_works` — REST path ignores session parameter — non-None is tolerated.

**TestCredentialValidation** — Test credential behavior with live tokens.

- `test_token_expiry_auto_detected` — JWT exp claim should be automatically extracted.
- `test_token_not_expired` — The token used for testing should not be expired.
