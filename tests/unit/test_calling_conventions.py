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
                assert len(deprecation_warnings) == 0, (
                    f"{func.__name__}: unexpected DeprecationWarning about session"
                )


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
                assert len(deprecation_warnings) == 1, (
                    f"{func.__name__}: expected 1 DeprecationWarning about session, got {len(deprecation_warnings)}"
                )


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


class TestSessionKeywordBackwardCompat:
    """
    Pattern 4: collect_*(session=None, creds=creds, ...) — historic keyword form.

    This is the calling convention shown throughout the old README / examples.
    It must work (with a DeprecationWarning) instead of raising TypeError.
    """

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_session_kwarg_none_warns_and_succeeds(self, func, patch_target, kwargs):
        """`session=None, creds=creds` should emit DeprecationWarning, not TypeError."""
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
                    func(session=None, creds=creds, **kwargs)
                except TypeError as e:
                    pytest.fail(
                        f"{func.__name__}(session=None, creds=creds) raised TypeError: {e}"
                    )
                except Exception:
                    pass  # mocks may not return valid data

                deprecation_warnings = [
                    x
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                    and "session" in str(x.message).lower()
                ]
                assert len(deprecation_warnings) >= 1, (
                    f"{func.__name__}: expected DeprecationWarning about session kwarg"
                )

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_session_kwarg_non_none_raises_soap_error(self, func, patch_target, kwargs):
        """`session=<truthy>, creds=creds` should still reject SOAP-style calls."""
        creds = _make_creds()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(SOAPDeprecationError):
                func(session="fake_conn", creds=creds, **kwargs)


from ffiec_data_connect.exceptions import ValidationError  # noqa: E402

# ---------------------------------------------------------------------------
# A. force_null_types accepted on all 7 methods
# ---------------------------------------------------------------------------


class TestForceNullTypesAcceptedByAllMethods:
    """force_null_types must be accepted on every collect_* method.

    Before rc4 this kwarg existed only on collect_data and
    collect_ubpr_facsimile_data; passing it to any other method raised
    TypeError. Now it's accepted (and acts as a no-op on list-returning
    methods, documented in each docstring).
    """

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_force_null_types_pandas_no_typeerror(self, func, patch_target, kwargs):
        """`force_null_types="pandas"` should not raise TypeError on any method."""
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

            try:
                func(creds, force_null_types="pandas", **kwargs)
            except TypeError as e:
                if "force_null_types" in str(e):
                    pytest.fail(
                        f"{func.__name__}(force_null_types='pandas') raised TypeError: {e}"
                    )
                raise
            except Exception:
                pass  # mocks may produce other exceptions downstream

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_force_null_types_invalid_value_raises_validation_error(
        self, func, patch_target, kwargs
    ):
        """Invalid force_null_types value must raise ValidationError on every method."""
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

            with pytest.raises((ValidationError, ValueError)):
                func(creds, force_null_types="garbage_value", **kwargs)


# ---------------------------------------------------------------------------
# B. output_type: xbrl / pdf / bytes (deprecated)
# ---------------------------------------------------------------------------

# Methods that support `xbrl` (facsimile endpoints only)
_XBRL_SUPPORTING_METHODS = {"collect_data", "collect_ubpr_facsimile_data"}

# Methods that support `pdf` (Call Report facsimile only — UBPR has no PDF)
_PDF_SUPPORTING_METHODS = {"collect_data"}


class TestOutputTypeXbrl:
    """`output_type="xbrl"` returns raw XBRL bytes on facsimile endpoints."""

    def test_collect_data_xbrl_returns_bytes(self):
        """collect_data(..., output_type='xbrl') returns XBRL bytes from the adapter."""
        from ffiec_data_connect.methods import collect_data

        creds = _make_creds()
        with patch(
            "ffiec_data_connect.protocol_adapter.create_protocol_adapter"
        ) as mock_create:
            mock_adapter = Mock()
            mock_adapter.retrieve_facsimile.return_value = (
                b'<?xml version="1.0"?><xbrl/>'
            )
            mock_create.return_value = mock_adapter

            result = collect_data(
                creds,
                reporting_period="12/31/2025",
                rssd_id="480228",
                series="call",
                output_type="xbrl",
            )

        assert isinstance(result, bytes)
        assert result.startswith(b"<?xml")

    def test_collect_ubpr_facsimile_xbrl_returns_bytes(self):
        """collect_ubpr_facsimile_data(..., output_type='xbrl') returns XBRL bytes."""
        from ffiec_data_connect.methods import collect_ubpr_facsimile_data

        creds = _make_creds()
        with patch(
            "ffiec_data_connect.protocol_adapter.create_protocol_adapter"
        ) as mock_create:
            mock_adapter = Mock()
            mock_adapter.retrieve_ubpr_xbrl_facsimile.return_value = (
                b'<?xml version="1.0"?><xbrl/>'
            )
            mock_create.return_value = mock_adapter

            result = collect_ubpr_facsimile_data(
                creds,
                reporting_period="12/31/2025",
                rssd_id="480228",
                output_type="xbrl",
            )

        assert isinstance(result, bytes)
        assert result.startswith(b"<?xml")

    @pytest.mark.parametrize(
        "func,patch_target,kwargs",
        [
            cfg
            for cfg in METHOD_CONFIGS
            if cfg[0].__name__ not in _XBRL_SUPPORTING_METHODS
        ],
        ids=[
            cfg[0].__name__
            for cfg in METHOD_CONFIGS
            if cfg[0].__name__ not in _XBRL_SUPPORTING_METHODS
        ],
    )
    def test_xbrl_rejected_on_non_facsimile_methods(self, func, patch_target, kwargs):
        """`output_type='xbrl'` must raise ValidationError on non-facsimile methods."""
        creds = _make_creds()
        with pytest.raises((ValidationError, ValueError)):
            func(creds, output_type="xbrl", **kwargs)


class TestOutputTypePdf:
    """`output_type="pdf"` returns raw PDF bytes on collect_data (Call Reports only)."""

    def test_collect_data_pdf_returns_bytes(self):
        """collect_data(series='call', output_type='pdf') returns PDF bytes."""
        from ffiec_data_connect.methods import collect_data

        creds = _make_creds()
        with patch(
            "ffiec_data_connect.protocol_adapter.create_protocol_adapter"
        ) as mock_create:
            mock_adapter = Mock()
            mock_adapter.retrieve_facsimile.return_value = b"%PDF-1.4\n...pdf bytes..."
            mock_create.return_value = mock_adapter

            result = collect_data(
                creds,
                reporting_period="12/31/2025",
                rssd_id="480228",
                series="call",
                output_type="pdf",
            )

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")

    def test_collect_data_pdf_rejected_for_ubpr(self):
        """collect_data(series='ubpr', output_type='pdf') must raise (UBPR endpoint is XBRL-only)."""
        from ffiec_data_connect.methods import collect_data

        creds = _make_creds()
        with pytest.raises((ValidationError, ValueError)):
            collect_data(
                creds,
                reporting_period="12/31/2025",
                rssd_id="480228",
                series="ubpr",
                output_type="pdf",
            )

    def test_collect_ubpr_facsimile_pdf_rejected(self):
        """collect_ubpr_facsimile_data does not support PDF; must raise."""
        from ffiec_data_connect.methods import collect_ubpr_facsimile_data

        creds = _make_creds()
        with pytest.raises((ValidationError, ValueError)):
            collect_ubpr_facsimile_data(
                creds,
                reporting_period="12/31/2025",
                rssd_id="480228",
                output_type="pdf",
            )

    @pytest.mark.parametrize(
        "func,patch_target,kwargs",
        [
            cfg
            for cfg in METHOD_CONFIGS
            if cfg[0].__name__ not in _PDF_SUPPORTING_METHODS
        ],
        ids=[
            cfg[0].__name__
            for cfg in METHOD_CONFIGS
            if cfg[0].__name__ not in _PDF_SUPPORTING_METHODS
        ],
    )
    def test_pdf_rejected_on_other_methods(self, func, patch_target, kwargs):
        """`output_type='pdf'` must raise on every method except collect_data."""
        creds = _make_creds()
        with pytest.raises((ValidationError, ValueError)):
            func(creds, output_type="pdf", **kwargs)


class TestOutputTypeBytesDeprecated:
    """`output_type="bytes"` is deprecated in rc4.

    Kept as a backward-compat alias for ``"xbrl"`` on collect_ubpr_facsimile_data
    (warns but works). Raises ValidationError elsewhere.
    """

    def test_bytes_on_ubpr_facsimile_warns_and_works(self):
        """collect_ubpr_facsimile_data(output_type='bytes') should warn and still return bytes."""
        from ffiec_data_connect.methods import collect_ubpr_facsimile_data

        creds = _make_creds()
        with patch(
            "ffiec_data_connect.protocol_adapter.create_protocol_adapter"
        ) as mock_create:
            mock_adapter = Mock()
            mock_adapter.retrieve_ubpr_xbrl_facsimile.return_value = (
                b'<?xml version="1.0"?><xbrl/>'
            )
            mock_create.return_value = mock_adapter

            with pytest.warns(DeprecationWarning, match="bytes"):
                result = collect_ubpr_facsimile_data(
                    creds,
                    reporting_period="12/31/2025",
                    rssd_id="480228",
                    output_type="bytes",
                )

        assert isinstance(result, bytes)

    @pytest.mark.parametrize(
        "func,patch_target,kwargs",
        [
            cfg
            for cfg in METHOD_CONFIGS
            if cfg[0].__name__ != "collect_ubpr_facsimile_data"
        ],
        ids=[
            cfg[0].__name__
            for cfg in METHOD_CONFIGS
            if cfg[0].__name__ != "collect_ubpr_facsimile_data"
        ],
    )
    def test_bytes_on_other_methods_warns_and_raises(self, func, patch_target, kwargs):
        """Every non-facsimile method must warn AND raise on output_type='bytes'."""
        creds = _make_creds()

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with pytest.raises((ValidationError, ValueError)):
                func(creds, output_type="bytes", **kwargs)

        deprecations = [
            w
            for w in captured
            if issubclass(w.category, DeprecationWarning)
            and "bytes" in str(w.message).lower()
        ]
        assert len(deprecations) >= 1, (
            f"{func.__name__}: expected DeprecationWarning about output_type='bytes'"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
