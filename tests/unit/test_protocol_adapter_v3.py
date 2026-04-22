"""
Unit tests for protocol_adapter.py

Tests the parts of the protocol adapter module that do NOT require
a live FFIEC API connection: response handling, validation, rate limiting,
factory function, and SOAP deprecation stub.
"""

from unittest.mock import Mock, PropertyMock, patch

import httpx
import pytest

from ffiec_data_connect.config import Config
from ffiec_data_connect.credentials import OAuth2Credentials, WebserviceCredentials
from ffiec_data_connect.exceptions import (
    ConnectionError,
    CredentialError,
    FFIECError,
    NoDataError,
    RateLimitError,
    SOAPDeprecationError,
    ValidationError,
)
from ffiec_data_connect.protocol_adapter import (
    RateLimiter,
    RESTAdapter,
    SOAPAdapter,
    create_protocol_adapter,
)


@pytest.fixture(autouse=True)
def _disable_legacy_errors():
    """Disable legacy errors so tests get specific exception types."""
    Config.set_legacy_errors(False)
    yield
    Config.reset()


# Test JWT: {"alg":"none","typ":"JWT"}.{"sub":"test","exp":1783442253} (far future)
TEST_JWT = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
)


def _make_creds() -> OAuth2Credentials:
    """Create real OAuth2Credentials with a test JWT for use in tests."""
    return OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)


def _make_rest_adapter() -> RESTAdapter:
    """Create a RESTAdapter with mocked httpx.Client to avoid real connections."""
    creds = _make_creds()
    with patch("httpx.Client"):
        adapter = RESTAdapter(creds)
    return adapter


def _make_mock_response(
    status_code: int,
    json_data=None,
    text: str = "",
    headers: dict = None,
) -> Mock:
    """Create a mock httpx.Response with the given attributes."""
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text
    response.headers = headers or {}

    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = ValueError("No JSON")

    return response


# ---------------------------------------------------------------------------
# RESTAdapter._handle_response
# ---------------------------------------------------------------------------
class TestRESTAdapterHandleResponse:
    """Tests for RESTAdapter._handle_response status code handling."""

    def test_200_returns_json(self):
        """HTTP 200 should parse and return JSON body."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(200, json_data=["12/31/2023", "6/30/2023"])

        result = adapter._handle_response(response, "TestEndpoint")

        assert result == ["12/31/2023", "6/30/2023"]

    def test_200_invalid_json_raises_ffiec_error(self):
        """HTTP 200 with unparseable body should raise FFIECError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(200)
        response.json.side_effect = ValueError("bad json")

        with pytest.raises(FFIECError, match="Invalid JSON"):
            adapter._handle_response(response, "TestEndpoint")

    def test_204_returns_empty_list(self):
        """HTTP 204 (No Content) should return an empty list."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(204)

        result = adapter._handle_response(response, "TestEndpoint")

        assert result == []

    def test_400_raises_validation_error(self):
        """HTTP 400 should raise ValidationError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(400, text="Bad request params")

        with pytest.raises(ValidationError):
            adapter._handle_response(response, "TestEndpoint")

    def test_401_raises_credential_error(self):
        """HTTP 401 should raise CredentialError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(401)

        with pytest.raises(CredentialError, match="OAuth2 authentication failed"):
            adapter._handle_response(response, "TestEndpoint")

    def test_403_raises_credential_error(self):
        """HTTP 403 should raise CredentialError with detailed message."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(403)

        with pytest.raises(CredentialError, match="Access forbidden"):
            adapter._handle_response(response, "TestEndpoint")

    def test_404_raises_no_data_error(self):
        """HTTP 404 should raise NoDataError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(404)

        with pytest.raises(NoDataError, match="No data found"):
            adapter._handle_response(response, "TestEndpoint")

    def test_429_raises_rate_limit_error(self):
        """HTTP 429 should raise RateLimitError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(429, headers={"Retry-After": "120"})

        with pytest.raises(RateLimitError):
            adapter._handle_response(response, "TestEndpoint")

    def test_429_with_non_numeric_retry_after(self):
        """HTTP 429 with non-numeric Retry-After defaults to 60 seconds."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(429, headers={"Retry-After": "not-a-number"})

        with pytest.raises(RateLimitError) as exc_info:
            adapter._handle_response(response, "TestEndpoint")

        assert exc_info.value.details.get("retry_after_seconds") == 60

    def test_429_without_retry_after_header(self):
        """HTTP 429 without Retry-After header defaults to 60 seconds."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(429, headers={})

        with pytest.raises(RateLimitError) as exc_info:
            adapter._handle_response(response, "TestEndpoint")

        assert exc_info.value.details.get("retry_after_seconds") == 60

    def test_500_raises_connection_error(self):
        """HTTP 500 should raise ConnectionError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(500)

        with pytest.raises(ConnectionError, match="server error"):
            adapter._handle_response(response, "TestEndpoint")

    def test_unexpected_status_raises_ffiec_error(self):
        """Unexpected status codes should raise FFIECError."""
        adapter = _make_rest_adapter()
        response = _make_mock_response(503, text="Service Unavailable")

        with pytest.raises(FFIECError, match="Unexpected response"):
            adapter._handle_response(response, "TestEndpoint")


# ---------------------------------------------------------------------------
# RESTAdapter._validate_response
# ---------------------------------------------------------------------------
class TestRESTAdapterValidateResponse:
    """Tests for RESTAdapter._validate_response Pydantic validation wrapper."""

    def test_root_model_unwraps_root(self):
        """Models with a root attribute should return root data."""
        adapter = _make_rest_adapter()

        mock_model_class = Mock()
        mock_instance = Mock()
        mock_instance.root = ["12/31/2023", "6/30/2023"]
        mock_model_class.return_value = mock_instance

        result = adapter._validate_response(
            ["12/31/2023", "6/30/2023"], mock_model_class, "TestEndpoint"
        )

        assert result == ["12/31/2023", "6/30/2023"]

    def test_nested_root_models_unwrapped(self):
        """Nested RootModels should be flattened: each item.root extracted."""
        adapter = _make_rest_adapter()

        inner1 = Mock()
        inner1.root = "12/31/2023"
        inner2 = Mock()
        inner2.root = "6/30/2023"

        mock_model_class = Mock()
        mock_instance = Mock()
        mock_instance.root = [inner1, inner2]
        mock_model_class.return_value = mock_instance

        result = adapter._validate_response(
            ["12/31/2023", "6/30/2023"], mock_model_class, "TestEndpoint"
        )

        assert result == ["12/31/2023", "6/30/2023"]

    def test_regular_model_returned_as_is(self):
        """Models without root attribute should be returned as the validated instance."""
        adapter = _make_rest_adapter()

        mock_model_class = Mock()
        mock_instance = Mock(spec=[])  # Empty spec -- no 'root' attribute
        mock_model_class.return_value = mock_instance

        result = adapter._validate_response(
            {"key": "value"}, mock_model_class, "TestEndpoint"
        )

        assert result is mock_instance

    def test_pydantic_validation_error_raises_validation_error(self):
        """Pydantic ValidationError should be caught and re-raised as our ValidationError."""
        from pydantic import ValidationError as PydanticValidationError

        adapter = _make_rest_adapter()

        mock_model_class = Mock()
        mock_model_class.side_effect = PydanticValidationError.from_exception_data(
            title="test",
            line_errors=[
                {
                    "type": "missing",
                    "loc": ("field",),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )

        with pytest.raises(ValidationError):
            adapter._validate_response(
                {"bad": "data"}, mock_model_class, "TestEndpoint"
            )


# ---------------------------------------------------------------------------
# RESTAdapter properties
# ---------------------------------------------------------------------------
class TestRESTAdapterProperties:
    """Tests for RESTAdapter property and helper methods."""

    def test_protocol_name_is_rest(self):
        """protocol_name should return 'REST'."""
        adapter = _make_rest_adapter()
        assert adapter.protocol_name == "REST"

    def test_is_rest_returns_true(self):
        """is_rest() should return True."""
        adapter = _make_rest_adapter()
        assert adapter.is_rest() is True


# ---------------------------------------------------------------------------
# RateLimiter.__init__
# ---------------------------------------------------------------------------
class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_default_parameters(self):
        """Default init should set 2500 calls/hour and 0.69 calls/sec."""
        limiter = RateLimiter()

        assert limiter.calls_per_hour == 2500
        assert limiter.calls_per_second == 0.69
        assert limiter.min_interval == pytest.approx(1.0 / 0.69, rel=1e-6)
        assert limiter.last_call == 0.0
        assert limiter.call_history == []

    def test_custom_parameters(self):
        """Custom parameters should override defaults."""
        limiter = RateLimiter(calls_per_hour=1000, calls_per_second=2.0)

        assert limiter.calls_per_hour == 1000
        assert limiter.calls_per_second == 2.0
        assert limiter.min_interval == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# RateLimiter.wait_if_needed
# ---------------------------------------------------------------------------
class TestRateLimiterWaitIfNeeded:
    """Tests for RateLimiter.wait_if_needed timing logic."""

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_sleeps_when_under_interval(self, mock_time):
        """Should sleep when the time since last call is less than min_interval."""
        limiter = RateLimiter(calls_per_second=2.0)  # min_interval = 0.5s

        # First call at t=100.0
        mock_time.time.return_value = 100.0
        mock_time.sleep = Mock()
        limiter.wait_if_needed()

        # Second call at t=100.1 (only 0.1s later, need 0.5s)
        mock_time.time.return_value = 100.1
        limiter.wait_if_needed()

        # Should have slept for ~0.4s (0.5 - 0.1)
        mock_time.sleep.assert_called()
        sleep_duration = mock_time.sleep.call_args_list[-1][0][0]
        assert sleep_duration == pytest.approx(0.4, abs=0.05)

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_no_sleep_when_enough_time_passed(self, mock_time):
        """Should not sleep when enough time has passed since last call."""
        limiter = RateLimiter(calls_per_second=2.0)  # min_interval = 0.5s

        # First call at t=100.0
        mock_time.time.return_value = 100.0
        mock_time.sleep = Mock()
        limiter.wait_if_needed()

        # Second call at t=101.0 (1.0s later, well past 0.5s minimum)
        mock_time.time.return_value = 101.0
        limiter.wait_if_needed()

        # sleep should not have been called (or only called on first iteration)
        # The first call never needs to sleep (last_call starts at 0.0, so
        # time_since_last = 100.0 which is huge).
        # The second call also shouldn't sleep since 1.0 > 0.5
        # Check that sleep was not called at all
        mock_time.sleep.assert_not_called()

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_records_call_in_history(self, mock_time):
        """Each call to wait_if_needed should add a timestamp to call_history."""
        limiter = RateLimiter(calls_per_second=1.0)

        mock_time.time.return_value = 100.0
        mock_time.sleep = Mock()
        limiter.wait_if_needed()

        assert len(limiter.call_history) == 1
        assert limiter.call_history[0] == 100.0

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_cleans_old_calls(self, mock_time):
        """Calls older than 1 hour should be cleaned from history."""
        limiter = RateLimiter(calls_per_second=0.5)

        mock_time.sleep = Mock()

        # Add an old call at t=0.0
        mock_time.time.return_value = 0.0
        limiter.wait_if_needed()
        assert len(limiter.call_history) == 1

        # New call at t=7200 (2 hours later) -- old call should be cleaned
        mock_time.time.return_value = 7200.0
        limiter.wait_if_needed()
        assert len(limiter.call_history) == 1  # old one cleaned, new one added
        assert limiter.call_history[0] == 7200.0


# ---------------------------------------------------------------------------
# RateLimiter.get_stats
# ---------------------------------------------------------------------------
class TestRateLimiterGetStats:
    """Tests for RateLimiter.get_stats."""

    def test_stats_structure(self):
        """get_stats should return a dict with expected keys."""
        limiter = RateLimiter()
        stats = limiter.get_stats()

        assert isinstance(stats, dict)
        assert "calls_this_hour" in stats
        assert "hourly_limit" in stats
        assert "hourly_remaining" in stats
        assert "per_second_limit" in stats
        assert "last_call_seconds_ago" in stats

    def test_initial_stats_values(self):
        """Initial stats should show zero calls and full quota."""
        limiter = RateLimiter(calls_per_hour=2500, calls_per_second=0.69)
        stats = limiter.get_stats()

        assert stats["calls_this_hour"] == 0
        assert stats["hourly_limit"] == 2500
        assert stats["hourly_remaining"] == 2500
        assert stats["per_second_limit"] == 0.69
        assert stats["last_call_seconds_ago"] is None  # No calls yet

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_stats_after_calls(self, mock_time):
        """Stats should reflect calls made."""
        mock_time.sleep = Mock()
        limiter = RateLimiter(calls_per_hour=2500, calls_per_second=0.5)

        mock_time.time.return_value = 100.0
        limiter.wait_if_needed()

        mock_time.time.return_value = 105.0
        limiter.wait_if_needed()

        mock_time.time.return_value = 110.0
        stats = limiter.get_stats()

        assert stats["calls_this_hour"] == 2
        assert stats["hourly_remaining"] == 2498


# ---------------------------------------------------------------------------
# create_protocol_adapter factory
# ---------------------------------------------------------------------------
class TestCreateProtocolAdapter:
    """Tests for the create_protocol_adapter factory function."""

    @patch("httpx.Client")
    def test_oauth2_credentials_returns_rest_adapter(self, mock_httpx_client):
        """OAuth2Credentials should produce a RESTAdapter."""
        creds = _make_creds()
        adapter = create_protocol_adapter(creds)

        assert isinstance(adapter, RESTAdapter)

    def test_webservice_credentials_raises_soap_deprecation(self):
        """WebserviceCredentials should raise SOAPDeprecationError."""
        # WebserviceCredentials.__init__ itself raises SOAPDeprecationError,
        # so we use a Mock with the right spec to bypass __init__.
        mock_creds = Mock(spec=WebserviceCredentials)

        with pytest.raises(SOAPDeprecationError):
            create_protocol_adapter(mock_creds)

    def test_invalid_credential_type_raises_credential_error(self):
        """Unsupported credential types should raise CredentialError."""
        with pytest.raises(CredentialError, match="Unsupported credential type"):
            create_protocol_adapter("not_a_credential_object")

    @patch("httpx.Client")
    def test_session_passed_to_rest_adapter(self, mock_httpx_client):
        """Session parameter should be accepted (even if ignored for REST)."""
        creds = _make_creds()
        mock_session = Mock()
        adapter = create_protocol_adapter(creds, session=mock_session)

        assert isinstance(adapter, RESTAdapter)


# ---------------------------------------------------------------------------
# SOAPAdapter stub
# ---------------------------------------------------------------------------
class TestSOAPAdapter:
    """Tests for the deprecated SOAPAdapter stub."""

    def test_init_raises_soap_deprecation_error(self):
        """SOAPAdapter instantiation should always raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            SOAPAdapter()

        assert "SOAP" in str(exc_info.value)
        assert "shut down" in str(exc_info.value).lower() or "DISCONTINUED" in str(
            exc_info.value
        )

    def test_init_with_args_raises_soap_deprecation_error(self):
        """SOAPAdapter instantiation with any args should raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            SOAPAdapter("arg1", key="val")

    def test_error_message_contains_migration_info(self):
        """SOAPDeprecationError should contain migration guidance."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            SOAPAdapter()

        error_msg = str(exc_info.value)
        assert "RESTAdapter" in error_msg
        assert "OAuth2Credentials" in error_msg


# ---------------------------------------------------------------------------
# RESTAdapter.__init__ credential check (line 201)
# ---------------------------------------------------------------------------
class TestRESTAdapterInitCredentialCheck:
    """Tests for RESTAdapter.__init__ rejecting non-OAuth2 credentials."""

    def test_non_oauth2_credentials_raises_credential_error(self):
        """Passing non-OAuth2Credentials to RESTAdapter raises CredentialError (line 201)."""
        with pytest.raises(
            CredentialError, match="RESTAdapter requires OAuth2Credentials"
        ):
            RESTAdapter(Mock())  # Mock without spec=OAuth2Credentials


# ---------------------------------------------------------------------------
# RESTAdapter._make_request (lines 262, 266)
# ---------------------------------------------------------------------------
class TestRESTAdapterMakeRequest:
    """Tests for RESTAdapter._make_request method body."""

    def test_make_request_with_params_and_additional_headers(self):
        """_make_request passes params and additional_headers to the request (lines 262, 266)."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = _make_mock_response(200, json_data=["period1", "period2"])
        mock_response.text = ""
        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter._make_request(
            "TestEndpoint",
            params={"dataSeries": "Call"},
            additional_headers={"X-Custom": "value"},
        )

        adapter.rate_limiter.wait_if_needed.assert_called_once()
        adapter.client.get.assert_called_once()
        assert result == ["period1", "period2"]

        # Verify headers include params and additional_headers
        call_kwargs = adapter.client.get.call_args
        headers = (
            call_kwargs[1]["headers"]
            if "headers" in call_kwargs[1]
            else call_kwargs[0][1]
        )
        assert headers.get("dataSeries") == "Call"
        assert headers.get("X-Custom") == "value"


# ---------------------------------------------------------------------------
# RESTAdapter.retrieve_reporting_periods (lines 448-467)
# ---------------------------------------------------------------------------
class TestRESTAdapterRetrieveReportingPeriods:
    """Tests for RESTAdapter.retrieve_reporting_periods body."""

    @patch("ffiec_data_connect.protocol_adapter.DataNormalizer.normalize_response")
    def test_retrieve_reporting_periods_call(self, mock_normalize):
        """retrieve_reporting_periods normalizes and validates response (lines 448-467)."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=["12/31/2023", "6/30/2023"])
        mock_normalize.return_value = ["12/31/2023", "6/30/2023"]

        # Mock _validate_response to return the data directly
        adapter._validate_response = Mock(return_value=["12/31/2023", "6/30/2023"])

        result = adapter.retrieve_reporting_periods("call")

        adapter._make_request.assert_called_once()
        mock_normalize.assert_called_once_with(
            ["12/31/2023", "6/30/2023"], "RetrieveReportingPeriods", "REST"
        )
        assert result == ["12/31/2023", "6/30/2023"]

    @patch("ffiec_data_connect.protocol_adapter.DataNormalizer.normalize_response")
    def test_retrieve_reporting_periods_ubpr(self, mock_normalize):
        """retrieve_reporting_periods with UBPR series uses UBPR validation (lines 457-462)."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=["12/31/2023"])
        mock_normalize.return_value = ["12/31/2023"]
        adapter._validate_response = Mock(return_value=["12/31/2023"])

        result = adapter.retrieve_reporting_periods("ubpr")

        assert result == ["12/31/2023"]


# ---------------------------------------------------------------------------
# RESTAdapter.retrieve_facsimile JSON/base64 path (lines 549-572)
# ---------------------------------------------------------------------------
class TestRESTAdapterRetrieveFacsimile:
    """Tests for RESTAdapter.retrieve_facsimile JSON+base64 decoding."""

    def test_facsimile_json_base64_string(self):
        """JSON response with base64-encoded string is decoded (lines 527-535)."""
        import base64

        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        xbrl_data = b"<xbrl>test data</xbrl>"
        encoded = base64.b64encode(xbrl_data).decode()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = encoded
        mock_response.content = b"raw content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter.retrieve_facsimile("480228", "12/31/2023", "call")

        assert result == xbrl_data

    def test_facsimile_json_non_string_raises(self):
        """JSON response with non-string value raises ConnectionError (rc4).

        Previously the adapter silently returned ``response.content`` when
        the JSON envelope didn't match the expected ``str`` shape. A 200
        response with the wrong shape is an API contract break, so surface
        it rather than hand the caller a garbled body.
        """
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}  # Not a string
        mock_response.content = b"raw content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="unexpected JSON shape"):
            adapter.retrieve_facsimile("480228", "12/31/2023", "call")

    def test_facsimile_json_invalid_base64_raises(self):
        """JSON string that is not valid base64 raises ConnectionError.

        Defensive branch in the facsimile decoder: if FFIEC ever returns a
        200 with a JSON-wrapped string that isn't decodable as base64, we
        must not return garbled bytes to the caller. A ``ConnectionError``
        with an explicit "not valid base64" message is the right surface.
        """
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        # Non-base64-safe characters (@, #) trigger binascii.Error.
        mock_response.json.return_value = "not@valid#base64!"
        mock_response.content = b"raw content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="not valid base64"):
            adapter.retrieve_facsimile("480228", "12/31/2023", "call")

    def test_facsimile_404_raises_no_data_error(self):
        """404 response raises NoDataError (lines 549-552)."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "Not found"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(NoDataError, match="No data found for RSSD 480228"):
            adapter.retrieve_facsimile("480228", "12/31/2023", "call")

    def test_facsimile_500_raises_connection_error(self):
        """500 response raises ConnectionError.

        rc6 reworded the message from "may not be implemented yet" to the
        accurate "transient upstream" guidance (live tests confirm the
        endpoint is implemented and working).
        """
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.text = "Server error"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="HTTP 500|transient"):
            adapter.retrieve_facsimile("480228", "12/31/2023", "call")

    def test_facsimile_unexpected_status_raises_connection_error(self):
        """Unexpected status code raises ConnectionError (lines 563-568)."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 302
        mock_response.headers = {}
        mock_response.text = "Redirect"
        mock_response.json.side_effect = ValueError("no json")

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        # _handle_response for 302 raises FFIECError (unexpected status)
        with pytest.raises((ConnectionError, FFIECError)):
            adapter.retrieve_facsimile("480228", "12/31/2023", "call")


# ---------------------------------------------------------------------------
# RESTAdapter.retrieve_panel_of_reporters (lines 597-609)
# ---------------------------------------------------------------------------
class TestRESTAdapterRetrievePanelOfReporters:
    """Tests for RESTAdapter.retrieve_panel_of_reporters body."""

    @patch("ffiec_data_connect.protocol_adapter.DataNormalizer.normalize_response")
    def test_retrieve_panel_of_reporters(self, mock_normalize):
        """retrieve_panel_of_reporters normalizes and validates response (lines 597-609)."""
        adapter = _make_rest_adapter()
        raw_data = [{"id_rssd": "480228", "name": "Test Bank"}]
        adapter._make_request = Mock(return_value=raw_data)
        mock_normalize.return_value = raw_data
        adapter._validate_response = Mock(return_value=raw_data)

        result = adapter.retrieve_panel_of_reporters("12/31/2023")

        adapter._make_request.assert_called_once_with(
            "RetrievePanelOfReporters",
            {
                "reportingPeriodEndDate": "12/31/2023",
                "dataSeries": "Call",
            },
        )
        mock_normalize.assert_called_once_with(
            raw_data, "RetrievePanelOfReporters", "REST"
        )
        assert result == raw_data


# ---------------------------------------------------------------------------
# RESTAdapter.retrieve_filers_since_date (lines 641-653)
# ---------------------------------------------------------------------------
class TestRESTAdapterRetrieveFilersSinceDate:
    """Tests for RESTAdapter.retrieve_filers_since_date body."""

    @patch("ffiec_data_connect.protocol_adapter.DataNormalizer.normalize_response")
    def test_retrieve_filers_since_date(self, mock_normalize):
        """retrieve_filers_since_date normalizes and validates response (lines 641-653)."""
        adapter = _make_rest_adapter()
        raw_data = [480228, 480229]
        adapter._make_request = Mock(return_value=raw_data)
        mock_normalize.return_value = ["480228", "480229"]
        adapter._validate_response = Mock(return_value=["480228", "480229"])

        result = adapter.retrieve_filers_since_date("12/31/2023", "01/01/2023")

        adapter._make_request.assert_called_once_with(
            "RetrieveFilersSinceDate",
            {
                "reportingPeriodEndDate": "12/31/2023",
                "lastUpdateDateTime": "01/01/2023",
                "dataSeries": "Call",
            },
        )
        mock_normalize.assert_called_once_with(
            raw_data, "RetrieveFilersSinceDate", "REST"
        )
        assert result == ["480228", "480229"]


# ---------------------------------------------------------------------------
# RESTAdapter.retrieve_ubpr_reporting_periods (lines 740-752)
# ---------------------------------------------------------------------------
class TestRESTAdapterRetrieveUBPRReportingPeriods:
    """Tests for RESTAdapter.retrieve_ubpr_reporting_periods body."""

    @patch("ffiec_data_connect.protocol_adapter.DataNormalizer.normalize_response")
    def test_retrieve_ubpr_reporting_periods(self, mock_normalize):
        """retrieve_ubpr_reporting_periods normalizes and validates (lines 740-752)."""
        adapter = _make_rest_adapter()
        raw_data = ["12/31/2023", "9/30/2023"]
        adapter._make_request = Mock(return_value=raw_data)
        mock_normalize.return_value = raw_data
        adapter._validate_response = Mock(return_value=raw_data)

        result = adapter.retrieve_ubpr_reporting_periods()

        adapter._make_request.assert_called_once_with(
            "RetrieveUBPRReportingPeriods",
            params=None,
        )
        mock_normalize.assert_called_once_with(
            raw_data, "RetrieveUBPRReportingPeriods", "REST"
        )
        assert result == raw_data


# ---------------------------------------------------------------------------
# RESTAdapter.retrieve_ubpr_xbrl_facsimile JSON+base64 (lines 825-838)
# ---------------------------------------------------------------------------
class TestRESTAdapterRetrieveUBPRXBRLFacsimile:
    """Tests for RESTAdapter.retrieve_ubpr_xbrl_facsimile JSON/base64 path."""

    def test_ubpr_facsimile_json_base64_string(self):
        """JSON response with base64-encoded XBRL is decoded (lines 800-811)."""
        import base64

        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        xbrl_data = b"<xbrl>ubpr test data</xbrl>"
        encoded = base64.b64encode(xbrl_data).decode()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = encoded
        mock_response.content = b"raw content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter.retrieve_ubpr_xbrl_facsimile("480228", "12/31/2023")

        assert result == xbrl_data

    def test_ubpr_facsimile_json_non_string_raises(self):
        """JSON response with non-string value raises ConnectionError (rc4).

        See TestRESTAdapterRetrieveFacsimile.test_facsimile_json_non_string_raises
        for the rationale — a 200 with the wrong JSON shape is a contract
        break and must surface instead of silently handing back raw content.
        """
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}  # Not a string
        mock_response.content = b"raw ubpr content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="unexpected JSON shape"):
            adapter.retrieve_ubpr_xbrl_facsimile("480228", "12/31/2023")

    def test_ubpr_facsimile_json_invalid_base64_raises(self):
        """JSON string that is not valid base64 raises ConnectionError on the
        UBPR path — mirrors the Call-Report facsimile behavior.
        """
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = "not@valid#base64!"
        mock_response.content = b"raw ubpr content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="not valid base64"):
            adapter.retrieve_ubpr_xbrl_facsimile("480228", "12/31/2023")

    def test_ubpr_facsimile_404_raises_no_data_error(self):
        """404 response raises NoDataError (lines 825-828)."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "Not found"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(NoDataError, match="No UBPR data found"):
            adapter.retrieve_ubpr_xbrl_facsimile("480228", "12/31/2023")

    def test_ubpr_facsimile_unexpected_status_raises_error(self):
        """Unexpected status raises ConnectionError (lines 829-834)."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 302
        mock_response.headers = {}
        mock_response.text = "Redirect"
        mock_response.json.side_effect = ValueError("no json")

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises((ConnectionError, FFIECError)):
            adapter.retrieve_ubpr_xbrl_facsimile("480228", "12/31/2023")


# ---------------------------------------------------------------------------
# RateLimiter hourly limit with pre-filled history (lines 915->923)
# ---------------------------------------------------------------------------
class TestRateLimiterHourlyLimitPreFilled:
    """Tests for RateLimiter hourly limit branch with pre-filled call history."""

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_hourly_limit_triggers_sleep_with_full_history(self, mock_time):
        """When call_history has 2500 entries within the last hour, sleep is called (line 915)."""
        limiter = RateLimiter(calls_per_hour=2500, calls_per_second=100.0)

        now = 10000.0
        mock_time.time.return_value = now
        mock_time.sleep = Mock()

        # Pre-fill call_history with 2500 entries all within the last hour
        limiter.call_history = [now - 1800 + i * 0.5 for i in range(2500)]
        limiter.last_call = now - 10.0  # Enough time so per-second limit won't trigger

        limiter.wait_if_needed()

        # time.sleep should have been called for the hourly wait
        mock_time.sleep.assert_called()
        # First sleep call should be for the hourly limit wait
        first_sleep_arg = mock_time.sleep.call_args_list[0][0][0]
        assert first_sleep_arg > 0


# ---------------------------------------------------------------------------
# RESTAdapter.__init__ with expired token (line 220)
# ---------------------------------------------------------------------------
class TestRESTAdapterInitExpiredToken:
    """Tests for RESTAdapter initialization with expired credentials."""

    def test_expired_token_logs_warning(self, caplog):
        """RESTAdapter with expired token should log a warning on init."""
        creds = _make_creds()
        # Mock is_expired to return True
        with patch.object(
            type(creds), "is_expired", new_callable=PropertyMock, return_value=True
        ):
            with patch("httpx.Client"):
                import logging

                with caplog.at_level(
                    logging.WARNING, logger="ffiec_data_connect.protocol_adapter"
                ):
                    RESTAdapter(creds)
        assert any("expired" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# RESTAdapter._make_request — timeout / connect errors (lines 291-296)
# ---------------------------------------------------------------------------
class TestRESTAdapterMakeRequestErrors:
    """Tests for _make_request error handling branches."""

    def test_timeout_raises_connection_error(self):
        """httpx.TimeoutException should be caught and raised as ConnectionError."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.client = Mock()
        adapter.client.get.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(ConnectionError, match="timed out after 30 seconds"):
            adapter._make_request("TestEndpoint")

    def test_connect_error_raises_connection_error(self):
        """httpx.ConnectError should be caught and raised as ConnectionError."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.client = Mock()
        adapter.client.get.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(ConnectionError, match="Failed to connect"):
            adapter._make_request("TestEndpoint")

    def test_request_error_raises_ffiec_error(self):
        """httpx.RequestError should be caught and raised as FFIECError."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.client = Mock()
        adapter.client.get.side_effect = httpx.RequestError("general error")

        with pytest.raises(FFIECError, match="REST API request failed"):
            adapter._make_request("TestEndpoint")

    def test_expired_token_raises_credential_error(self):
        """_make_request with expired credentials should raise CredentialError."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        with patch.object(
            type(adapter.credentials),
            "is_expired",
            new_callable=PropertyMock,
            return_value=True,
        ):
            with pytest.raises(CredentialError, match="expired"):
                adapter._make_request("TestEndpoint")


# ---------------------------------------------------------------------------
# RESTAdapter._handle_response — 403 with expired token (lines 342-348)
# ---------------------------------------------------------------------------
class TestHandleResponse403Expired:
    """Tests for _handle_response 403 with token expiration details."""

    def test_403_with_expired_token_includes_expired_message(self):
        """HTTP 403 with expired token should include 'expired' in the error."""
        from datetime import datetime

        adapter = _make_rest_adapter()
        # Mock credentials with an expired token_expires
        adapter.credentials = Mock()
        adapter.credentials.token_expires = datetime(2020, 1, 1)

        response = _make_mock_response(403)

        with pytest.raises(CredentialError, match="expired"):
            adapter._handle_response(response, "TestEndpoint")


# ---------------------------------------------------------------------------
# RESTAdapter._handle_response — debug logging on error (line 287)
# ---------------------------------------------------------------------------
class TestHandleResponseDebugLogging:
    """Tests for debug logging of error response body."""

    def test_error_response_body_logged(self, caplog):
        """Error responses should log the response body in debug."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.client = Mock()

        mock_response = _make_mock_response(400, text="Bad request params")
        adapter.client.get.return_value = mock_response

        import logging

        with caplog.at_level(
            logging.DEBUG, logger="ffiec_data_connect.protocol_adapter"
        ):
            with pytest.raises(ValidationError):
                adapter._make_request("TestEndpoint")

        assert any("Error Response Body" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# retrieve_reporting_periods exception handler (lines 469-471)
# ---------------------------------------------------------------------------
class TestRetrieveReportingPeriodsException:
    """Tests for retrieve_reporting_periods exception re-raise."""

    def test_exception_is_reraised(self):
        """Exceptions in retrieve_reporting_periods should be logged and re-raised."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(side_effect=FFIECError("API failure"))

        with pytest.raises(FFIECError, match="API failure"):
            adapter.retrieve_reporting_periods("call")


# ---------------------------------------------------------------------------
# retrieve_facsimile with series="ubpr" (line 490)
# ---------------------------------------------------------------------------
class TestRetrieveFacsimileUBPR:
    """Tests for retrieve_facsimile routing to UBPR method."""

    def test_ubpr_series_routes_to_ubpr_method(self):
        """series='ubpr' should delegate to retrieve_ubpr_xbrl_facsimile."""
        adapter = _make_rest_adapter()
        adapter.retrieve_ubpr_xbrl_facsimile = Mock(return_value=b"<xbrl>ubpr</xbrl>")

        result = adapter.retrieve_facsimile(480228, "12/31/2023", "ubpr")

        adapter.retrieve_ubpr_xbrl_facsimile.assert_called_once_with(
            480228, "12/31/2023"
        )
        assert result == b"<xbrl>ubpr</xbrl>"


# ---------------------------------------------------------------------------
# retrieve_facsimile — JSON+base64 response (lines 537-572)
# ---------------------------------------------------------------------------
class TestRetrieveFacsimileResponses:
    """Tests for retrieve_facsimile response handling branches."""

    def test_json_base64_response_decoded(self):
        """JSON response with base64 string should be decoded to bytes."""
        import base64

        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        xbrl_content = b"<xbrl>test data</xbrl>"
        b64_encoded = base64.b64encode(xbrl_content).decode("ascii")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = b64_encoded

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter.retrieve_facsimile(480228, "12/31/2023", "call")
        assert result == xbrl_content

    def test_json_non_string_response_raises(self):
        """JSON response with the wrong shape raises ConnectionError (rc4).

        Prior behavior silently returned ``response.content``. A 200 with the
        wrong JSON shape is an API contract break — surface it instead.
        """
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}  # dict, not string
        mock_response.content = b"raw content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="unexpected JSON shape"):
            adapter.retrieve_facsimile(480228, "12/31/2023", "call")

    def test_non_json_response_returns_content(self):
        """Non-JSON response (e.g. application/xml) should return raw bytes."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.content = b"<xbrl>raw bytes</xbrl>"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter.retrieve_facsimile(480228, "12/31/2023", "call")
        assert result == b"<xbrl>raw bytes</xbrl>"

    def test_json_malformed_raises(self):
        """Malformed JSON body on a 200 response raises ConnectionError (rc4).

        Previously any Exception (including real bugs like AttributeError)
        was swallowed with a warning and raw bytes returned. Now only
        genuine JSON-parse failures are caught — and they surface as
        ConnectionError with the cause chained.
        """
        import json as _json

        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = _json.JSONDecodeError("nope", "", 0)
        mock_response.content = b"raw fallback"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="malformed JSON"):
            adapter.retrieve_facsimile(480228, "12/31/2023", "call")


# ---------------------------------------------------------------------------
# retrieve_panel_of_reporters exception (lines 611-615)
# ---------------------------------------------------------------------------
class TestRetrievePanelOfReportersException:
    """Tests for retrieve_panel_of_reporters exception re-raise."""

    def test_exception_is_reraised(self):
        """Exceptions should be logged and re-raised."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(side_effect=ConnectionError("network fail"))

        with pytest.raises(ConnectionError, match="network fail"):
            adapter.retrieve_panel_of_reporters("12/31/2023")


# ---------------------------------------------------------------------------
# retrieve_filers_since_date exception (lines 655-657)
# ---------------------------------------------------------------------------
class TestRetrieveFilersSinceDateException:
    """Tests for retrieve_filers_since_date exception re-raise."""

    def test_exception_is_reraised(self):
        """Exceptions should be logged and re-raised."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(side_effect=FFIECError("server error"))

        with pytest.raises(FFIECError, match="server error"):
            adapter.retrieve_filers_since_date("12/31/2023", "1/1/2023")


# ---------------------------------------------------------------------------
# retrieve_filers_submission_datetime — since_date=None (lines 684-699)
# ---------------------------------------------------------------------------
class TestRetrieveFilersSubmissionDatetimeNoSinceDate:
    """Tests for retrieve_filers_submission_datetime with since_date=None."""

    def test_q1_period_defaults_to_quarter_start(self):
        """Reporting period 03/31/2023 should default lastUpdateDateTime to 01/01/2023."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=[])

        with patch.object(adapter, "_validate_response", return_value=[]):
            adapter.retrieve_filers_submission_datetime("03/31/2023", since_date=None)

        call_args = adapter._make_request.call_args
        params = call_args[0][1]
        assert params["lastUpdateDateTime"] == "01/01/2023"

    def test_q2_period_defaults_to_quarter_start(self):
        """Reporting period 06/30/2023 should default lastUpdateDateTime to 04/01/2023."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=[])

        with patch.object(adapter, "_validate_response", return_value=[]):
            adapter.retrieve_filers_submission_datetime("06/30/2023", since_date=None)

        params = adapter._make_request.call_args[0][1]
        assert params["lastUpdateDateTime"] == "04/01/2023"

    def test_q3_period_defaults_to_quarter_start(self):
        """Reporting period 09/30/2023 should default lastUpdateDateTime to 07/01/2023."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=[])

        with patch.object(adapter, "_validate_response", return_value=[]):
            adapter.retrieve_filers_submission_datetime("09/30/2023", since_date=None)

        params = adapter._make_request.call_args[0][1]
        assert params["lastUpdateDateTime"] == "07/01/2023"

    def test_q4_period_defaults_to_quarter_start(self):
        """Reporting period 12/31/2023 should default lastUpdateDateTime to 10/01/2023."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=[])

        with patch.object(adapter, "_validate_response", return_value=[]):
            adapter.retrieve_filers_submission_datetime("12/31/2023", since_date=None)

        params = adapter._make_request.call_args[0][1]
        assert params["lastUpdateDateTime"] == "10/01/2023"

    def test_malformed_period_defaults_to_fallback(self):
        """A malformed reporting_period should use fallback date."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(return_value=[])

        with patch.object(adapter, "_validate_response", return_value=[]):
            adapter.retrieve_filers_submission_datetime("bad-date", since_date=None)

        params = adapter._make_request.call_args[0][1]
        assert params["lastUpdateDateTime"] == "01/01/2023"


# ---------------------------------------------------------------------------
# retrieve_filers_submission_datetime exception (lines 721-723)
# ---------------------------------------------------------------------------
class TestRetrieveFilersSubmissionDatetimeException:
    """Tests for retrieve_filers_submission_datetime exception re-raise."""

    def test_exception_is_reraised(self):
        """Exceptions should be logged and re-raised."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(side_effect=FFIECError("fail"))

        with pytest.raises(FFIECError, match="fail"):
            adapter.retrieve_filers_submission_datetime("12/31/2023", "1/1/2023")


# ---------------------------------------------------------------------------
# retrieve_ubpr_reporting_periods exception (lines 754-756)
# ---------------------------------------------------------------------------
class TestRetrieveUBPRReportingPeriodsException:
    """Tests for retrieve_ubpr_reporting_periods exception re-raise."""

    def test_exception_is_reraised(self):
        """Exceptions should be logged and re-raised."""
        adapter = _make_rest_adapter()
        adapter._make_request = Mock(side_effect=ConnectionError("timeout"))

        with pytest.raises(ConnectionError, match="timeout"):
            adapter.retrieve_ubpr_reporting_periods()


# ---------------------------------------------------------------------------
# retrieve_ubpr_xbrl_facsimile — JSON+base64 response (lines 813-838)
# ---------------------------------------------------------------------------
class TestRetrieveUBPRFacsimileResponses:
    """Tests for retrieve_ubpr_xbrl_facsimile response handling."""

    def test_json_base64_response_decoded(self):
        """JSON response with base64 string should be decoded to bytes."""
        import base64

        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        xbrl_content = b"<xbrl>ubpr test data</xbrl>"
        b64_encoded = base64.b64encode(xbrl_content).decode("ascii")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = b64_encoded

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter.retrieve_ubpr_xbrl_facsimile(480228, "12/31/2023")
        assert result == xbrl_content

    def test_json_non_string_response_raises(self):
        """JSON response with the wrong shape raises ConnectionError (rc4)."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"unexpected": "format"}
        mock_response.content = b"raw ubpr content"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="unexpected JSON shape"):
            adapter.retrieve_ubpr_xbrl_facsimile(480228, "12/31/2023")

    def test_non_json_response_returns_content(self):
        """Non-JSON response (e.g. application/xml) should return raw bytes."""
        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.content = b"<xbrl>raw ubpr</xbrl>"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        result = adapter.retrieve_ubpr_xbrl_facsimile(480228, "12/31/2023")
        assert result == b"<xbrl>raw ubpr</xbrl>"

    def test_json_malformed_raises(self):
        """Malformed JSON body raises ConnectionError (rc4).

        Prior behavior swallowed *any* exception (including real bugs) and
        returned raw bytes with a log warning.
        """
        import json as _json

        adapter = _make_rest_adapter()
        adapter.credentials = _make_creds()
        adapter.rate_limiter = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = _json.JSONDecodeError("bad", "", 0)
        mock_response.content = b"ubpr fallback"

        adapter.client = Mock()
        adapter.client.get.return_value = mock_response

        with pytest.raises(ConnectionError, match="malformed JSON"):
            adapter.retrieve_ubpr_xbrl_facsimile(480228, "12/31/2023")


# ---------------------------------------------------------------------------
# RateLimiter — hourly limit enforcement (lines 912-920)
# ---------------------------------------------------------------------------
class TestRateLimiterHourlyLimit:
    """Tests for RateLimiter hourly limit enforcement."""

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_hourly_limit_causes_sleep(self, mock_time):
        """When hourly limit is reached, should sleep until oldest call ages out."""
        limiter = RateLimiter(calls_per_hour=2, calls_per_second=100.0)
        mock_time.sleep = Mock()

        # First call at t=100
        mock_time.time.return_value = 100.0
        limiter.wait_if_needed()

        # Second call at t=101
        mock_time.time.return_value = 101.0
        limiter.wait_if_needed()

        # Third call at t=102 — hourly limit reached (2 calls in history)
        # oldest_call=100.0, need to wait until 100.0 + 3600 = 3700.0
        # wait_time = 3700.0 - 102.0 = 3598.0
        mock_time.time.return_value = 102.0
        limiter.wait_if_needed()

        # Should have slept for the hourly rate limit
        sleep_calls = [c for c in mock_time.sleep.call_args_list if c[0][0] > 100]
        assert len(sleep_calls) >= 1
        assert sleep_calls[0][0][0] == pytest.approx(3598.0, abs=1.0)


class TestHandleResponse403NoTokenExpires:
    """Cover branch 342->348: 403 response when token_expires is None."""

    def test_403_without_token_expires(self):
        """403 when credentials have no token_expires should not include expiry message."""
        adapter = _make_rest_adapter()
        # Set token_expires to None
        adapter.credentials._token_expires = None

        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with pytest.raises(CredentialError) as exc_info:
            adapter._handle_response(mock_response, "Test")
        # Should NOT mention "expired" since we don't know the expiry
        assert (
            "expired" not in str(exc_info.value).lower()
            or "verify" in str(exc_info.value).lower()
        )


class TestRateLimiterFiltersExpiredCalls:
    """When pre-existing call_history has entries older than 1 hour, the filter at the top of
    wait_if_needed() drops them before the hourly-limit check. Confirms the filter works.
    """

    @patch("ffiec_data_connect.protocol_adapter.time")
    def test_expired_history_is_filtered_before_limit_check(self, mock_time):
        """Entries at or below `now - 3600` must be filtered out, so the hourly block doesn't trigger."""
        limiter = RateLimiter(calls_per_hour=2500, calls_per_second=100.0)

        now = 10000.0
        mock_time.time.return_value = now

        # Fill history with 2500 calls all at now - 3601 (just over 1 hour ago). After the filter,
        # call_history should be empty and the hourly-limit branch never enters.
        limiter.call_history = [now - 3601 + i * 1e-6 for i in range(2500)]
        limiter.last_call = now - 10.0

        limiter.wait_if_needed()

        # The filter should have pruned the expired entries, so no long hourly sleep was issued.
        hourly_sleeps = [c for c in mock_time.sleep.call_args_list if c[0][0] > 10]
        assert len(hourly_sleeps) == 0
        # The newly-appended call is the only survivor (plus whatever the filter kept within the window).
        assert all(ts > now - 3600 for ts in limiter.call_history)


class TestXBRLRowSkipNone:
    """Cover xbrl_processor branch 119->118: empty row skipped."""

    def test_empty_row_in_items(self):
        """XBRL item that processes to None/empty should be skipped."""
        from ffiec_data_connect.xbrl_processor import _process_xml

        # XBRL with an element that has no value (empty text)
        xbrl_data = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:cc="http://www.ffiec.gov/call">
    <context id="ctx_1_2023-12-31">
        <entity><identifier>1</identifier></entity>
        <period><instant>2023-12-31</instant></period>
    </context>
    <cc:RCON0010 contextRef="ctx_1_2023-12-31" unitRef="USD" decimals="0">1000</cc:RCON0010>
</xbrl>"""
        result = _process_xml(xbrl_data, "string_original", False)
        # Should process without error, skipping any None rows
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# rc4: facsimile_format validation and UBPR-PDF guard on the adapter
# ---------------------------------------------------------------------------


class TestRESTAdapterFacsimileFormatValidation:
    """rc4: RESTAdapter.retrieve_facsimile must validate facsimile_format locally.

    The adapter is a public API (exported from the package top-level and
    referenced from the bytes-deprecation message as a lower-level escape
    hatch), so it must guard against:

    - unknown format strings being sent to the FFIEC server as a header
    - the UBPR-endpoint + PDF combination (UBPR is XBRL-only per spec); the
      high-level ``collect_data`` layer rejects this too, but adapter callers
      bypass that guard.
    """

    def test_invalid_facsimile_format_raises_locally(self):
        """A typo/unknown facsimile_format must raise before any network call."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()
        adapter.client = Mock()  # will assert not-called below

        with pytest.raises((ValidationError, ValueError)):
            adapter.retrieve_facsimile(
                "480228", "12/31/2024", "call", facsimile_format="XML"
            )

        # No HTTP call should have been made — rejection is local.
        adapter.client.get.assert_not_called()

    def test_empty_facsimile_format_raises(self):
        """Empty string is not a valid format."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()
        adapter.client = Mock()

        with pytest.raises((ValidationError, ValueError)):
            adapter.retrieve_facsimile(
                "480228", "12/31/2024", "call", facsimile_format=""
            )
        adapter.client.get.assert_not_called()

    def test_ubpr_with_pdf_raises_locally(self):
        """series='ubpr' + facsimile_format='PDF' must raise before the UBPR route."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()
        adapter.client = Mock()

        with pytest.raises((ValidationError, ValueError)):
            adapter.retrieve_facsimile(
                "480228", "12/31/2024", "ubpr", facsimile_format="PDF"
            )
        adapter.client.get.assert_not_called()

    def test_ubpr_with_xbrl_still_routes_to_ubpr_method(self):
        """series='ubpr' + facsimile_format='XBRL' must still delegate to the UBPR method."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()
        adapter.client = Mock()

        with patch.object(
            adapter, "retrieve_ubpr_xbrl_facsimile", return_value=b"<xbrl/>"
        ) as mock_ubpr:
            result = adapter.retrieve_facsimile(
                "480228", "12/31/2024", "ubpr", facsimile_format="XBRL"
            )

        mock_ubpr.assert_called_once_with("480228", "12/31/2024")
        assert result == b"<xbrl/>"

    def test_default_facsimile_format_is_xbrl(self):
        """Omitting facsimile_format should behave as XBRL (back-compat)."""
        adapter = _make_rest_adapter()
        adapter.rate_limiter = Mock()
        adapter.client = Mock()

        with patch.object(
            adapter, "retrieve_ubpr_xbrl_facsimile", return_value=b"<xbrl/>"
        ) as mock_ubpr:
            result = adapter.retrieve_facsimile("480228", "12/31/2024", "ubpr")

        mock_ubpr.assert_called_once()
        assert result == b"<xbrl/>"
