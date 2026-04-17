"""
Tests for the overloaded calling conventions on all 7 public methods.

Each method supports three calling patterns:
1. New style:  collect_*(creds, ...)           — preferred
2. Deprecated: collect_*(None, creds, ...)     — warns DeprecationWarning
3. SOAP error: collect_*(conn, creds, ...)     — raises SOAPDeprecationError
"""

import warnings
from unittest.mock import Mock, patch

import pytest

from ffiec_data_connect.config import Config
from ffiec_data_connect.credentials import OAuth2Credentials, WebserviceCredentials
from ffiec_data_connect.exceptions import SOAPDeprecationError
from ffiec_data_connect.methods import (
    _resolve_session_and_creds,
    collect_data,
    collect_filers_on_reporting_period,
    collect_filers_since_date,
    collect_filers_submission_date_time,
    collect_reporting_periods,
    collect_ubpr_facsimile_data,
    collect_ubpr_reporting_periods,
)

# Test JWT: {"alg":"none","typ":"JWT"}.{"sub":"test","exp":1783442253}
TEST_JWT = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
)


@pytest.fixture(autouse=True)
def _disable_legacy_and_suppress_token_warning():
    """Disable legacy errors and suppress bearer token warnings for all tests."""
    Config.set_legacy_errors(False)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Bearer token passed directly")
        yield
    Config.reset()


def _make_creds() -> OAuth2Credentials:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Bearer token passed directly")
        return OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)


# ---------------------------------------------------------------------------
# _resolve_session_and_creds (the core helper)
# ---------------------------------------------------------------------------


class TestResolveSessionAndCreds:
    """Test the shared helper that all 7 methods use."""

    def test_new_style_creds_first(self):
        """OAuth2Credentials as first arg → returned directly."""
        creds = _make_creds()
        result = _resolve_session_and_creds(creds)
        assert result is creds

    def test_old_style_none_session_warns(self):
        """None as first arg + creds second → DeprecationWarning."""
        creds = _make_creds()
        with pytest.warns(DeprecationWarning, match="session=None.*deprecated"):
            result = _resolve_session_and_creds(None, creds)
        assert result is creds

    def test_old_style_conn_session_raises(self):
        """Non-None, non-creds first arg → SOAPDeprecationError."""
        creds = _make_creds()
        with pytest.raises(SOAPDeprecationError):
            _resolve_session_and_creds("fake_connection", creds)

    def test_old_style_none_with_soap_creds_raises(self):
        """None + WebserviceCredentials → SOAPDeprecationError."""
        soap_creds = Mock(spec=WebserviceCredentials)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(SOAPDeprecationError):
                _resolve_session_and_creds(None, soap_creds)

    def test_old_style_none_with_invalid_creds_raises(self):
        """None + invalid second arg → ValidationError."""
        from ffiec_data_connect.exceptions import ValidationError

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises((ValidationError, ValueError)):
                _resolve_session_and_creds(None, "not_creds")

    def test_conn_without_creds_raises(self):
        """Non-None session without OAuth2 creds → SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            _resolve_session_and_creds("connection", None)


# ---------------------------------------------------------------------------
# Parametrized tests for all 7 methods
# ---------------------------------------------------------------------------

# Each method config: (func, patch_target, extra_kwargs)
METHOD_CONFIGS = [
    (
        collect_reporting_periods,
        "ffiec_data_connect.methods_enhanced.collect_reporting_periods_enhanced",
        {"series": "call"},
    ),
    (
        collect_data,
        "ffiec_data_connect.protocol_adapter.create_protocol_adapter",
        {"reporting_period": "12/31/2025", "rssd_id": "480228", "series": "call"},
    ),
    (
        collect_filers_since_date,
        "ffiec_data_connect.methods_enhanced.collect_filers_since_date_enhanced",
        {"reporting_period": "12/31/2025", "since_date": "1/1/2025"},
    ),
    (
        collect_filers_submission_date_time,
        "ffiec_data_connect.methods_enhanced.collect_filers_submission_date_time_enhanced",
        {"since_date": "1/1/2025", "reporting_period": "12/31/2025"},
    ),
    (
        collect_filers_on_reporting_period,
        "ffiec_data_connect.methods_enhanced.collect_filers_on_reporting_period_enhanced",
        {"reporting_period": "12/31/2025"},
    ),
    (
        collect_ubpr_reporting_periods,
        "ffiec_data_connect.protocol_adapter.create_protocol_adapter",
        {},
    ),
    (
        collect_ubpr_facsimile_data,
        "ffiec_data_connect.protocol_adapter.create_protocol_adapter",
        {"reporting_period": "12/31/2025", "rssd_id": "480228"},
    ),
]


def _method_ids():
    return [cfg[0].__name__ for cfg in METHOD_CONFIGS]


class TestNewStyleCredsFirst:
    """Pattern 1: collect_*(creds, ...) — preferred, no warnings."""

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_creds_first_no_warning(self, func, patch_target, kwargs):
        """Calling with creds as first arg should produce no DeprecationWarning."""
        creds = _make_creds()

        with patch(patch_target) as mock_target:
            # Set up mock return values
            if "create_protocol_adapter" in patch_target:
                mock_adapter = Mock()
                mock_adapter.retrieve_facsimile.return_value = b"<xbrl/>"
                mock_adapter.retrieve_ubpr_reporting_periods.return_value = [
                    "12/31/2025"
                ]
                mock_adapter.retrieve_ubpr_xbrl_facsimile.return_value = b"<xbrl/>"
                mock_target.return_value = mock_adapter
            else:
                mock_target.return_value = []

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    func(creds, **kwargs)
                except Exception:
                    pass  # Some mocks may not return valid data

                deprecation_warnings = [
                    x
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                    and "session=None" in str(x.message)
                ]
                assert (
                    len(deprecation_warnings) == 0
                ), f"{func.__name__}: unexpected DeprecationWarning about session"


class TestOldStyleNoneSession:
    """Pattern 2: collect_*(None, creds, ...) — deprecated, warns."""

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_none_session_warns(self, func, patch_target, kwargs):
        """Calling with None as first arg should emit DeprecationWarning."""
        creds = _make_creds()

        with patch(patch_target) as mock_target:
            if "create_protocol_adapter" in patch_target:
                mock_adapter = Mock()
                mock_adapter.retrieve_facsimile.return_value = b"<xbrl/>"
                mock_adapter.retrieve_ubpr_reporting_periods.return_value = [
                    "12/31/2025"
                ]
                mock_adapter.retrieve_ubpr_xbrl_facsimile.return_value = b"<xbrl/>"
                mock_target.return_value = mock_adapter
            else:
                mock_target.return_value = []

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                try:
                    func(None, creds, **kwargs)
                except Exception:
                    pass

                deprecation_warnings = [
                    x
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                    and "session=None" in str(x.message)
                ]
                assert (
                    len(deprecation_warnings) == 1
                ), f"{func.__name__}: expected 1 DeprecationWarning about session, got {len(deprecation_warnings)}"


class TestOldStyleConnSession:
    """Pattern 3: collect_*(conn, creds, ...) — raises SOAPDeprecationError."""

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_conn_session_raises(self, func, patch_target, kwargs):
        """Calling with a non-None session should raise SOAPDeprecationError."""
        creds = _make_creds()

        with pytest.raises(SOAPDeprecationError):
            func("fake_ffiec_connection", creds, **kwargs)


class TestOldStyleSoapCreds:
    """SOAP credentials should raise SOAPDeprecationError in all patterns."""

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_soap_creds_none_session_raises(self, func, patch_target, kwargs):
        """None + WebserviceCredentials → SOAPDeprecationError."""
        soap_creds = Mock(spec=WebserviceCredentials)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(SOAPDeprecationError):
                func(None, soap_creds, **kwargs)

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_soap_creds_as_first_arg_raises(self, func, patch_target, kwargs):
        """WebserviceCredentials as first arg → SOAPDeprecationError."""
        soap_creds = Mock(spec=WebserviceCredentials)
        with pytest.raises(SOAPDeprecationError):
            func(soap_creds, **kwargs)


# ---------------------------------------------------------------------------
# Bearer token env var warning
# ---------------------------------------------------------------------------


class TestBearerTokenWarning:
    """Test that hardcoded bearer tokens produce a warning."""

    def test_hardcoded_token_warns(self):
        """Creating OAuth2Credentials with literal token warns about env var."""
        import os

        with patch.dict(os.environ, {}, clear=True):
            with pytest.warns(UserWarning, match="FFIEC_BEARER_TOKEN"):
                OAuth2Credentials(username="user", bearer_token=TEST_JWT)

    def test_token_from_env_no_warning(self):
        """Creating OAuth2Credentials when env var matches produces no UserWarning."""
        import os

        with patch.dict(os.environ, {"FFIEC_BEARER_TOKEN": TEST_JWT}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                OAuth2Credentials(username="user", bearer_token=TEST_JWT)

                user_warnings = [
                    x
                    for x in w
                    if issubclass(x.category, UserWarning)
                    and "FFIEC_BEARER_TOKEN" in str(x.message)
                ]
                assert len(user_warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
