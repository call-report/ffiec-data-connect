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

    # ---- rc5 additions: helper-level coverage for kwarg-side paths --------

    def test_kwarg_creds_soap_raises(self):
        """(E3 helper-level) second_arg is WebserviceCredentials + first_arg
        not given → ``SOAPDeprecationError``. Exercises the rc5 fallback
        branch in the resolver.
        """
        soap_creds = Mock(spec=WebserviceCredentials)
        with pytest.raises(SOAPDeprecationError):
            _resolve_session_and_creds(second_arg=soap_creds)

    def test_session_truthy_alone_raises_soap(self):
        """(E8 helper-level) Only a truthy ``session=`` is passed (no creds at
        all). The session gets promoted to first_arg, hits the non-None-session
        branch, and raises ``SOAPDeprecationError`` — the session-kwarg
        deprecation is NOT emitted since the call isn't salvageable.
        """
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with pytest.raises(SOAPDeprecationError):
                _resolve_session_and_creds(session="fake_conn")

        session_kwarg_warnings = [
            w
            for w in captured
            if issubclass(w.category, DeprecationWarning)
            and "session" in str(w.message).lower()
            and "keyword" in str(w.message).lower()
        ]
        assert session_kwarg_warnings == [], (
            "Should not emit 'session kwarg deprecated' warning on paths that "
            "immediately raise SOAPDeprecationError"
        )

    def test_invalid_type_kwarg_creds_raises(self):
        """(V5) second_arg is a non-creds object (e.g. a string), first_arg
        not given → ``ValidationError``. rc5's fallback lands here when
        ``creds=<something unexpected>`` is passed.
        """
        from ffiec_data_connect.exceptions import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            _resolve_session_and_creds(second_arg="not_creds")


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


class TestNewStyleKwargCreds:
    """
    Pattern 5: ``collect_*(creds=creds, ...)`` — pure-kwarg new style, no
    session at all. This is the natural form for users writing everything
    as keyword arguments. It was broken in 3.0.0rc4 (raised
    ``ValueError: Missing credentials argument`` because the resolver
    checked only the first-positional slot) and fixed in rc5.
    """

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_pure_kwarg_creds_succeeds_without_warning(
        self, func, patch_target, kwargs
    ):
        """``func(creds=creds, ...)`` should reach the mocked downstream
        handler — proving the resolver didn't reject the pure-kwarg form.

        Asserting the mock was *called* is much stronger than asserting the
        error message doesn't contain a specific substring: it's the direct
        evidence that the resolver passed through. (rc4 silently failed this
        check because the error-message match was too permissive.)
        """
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
                    func(creds=creds, **kwargs)
                except Exception:
                    pass  # mock-depth noise is OK; the assertion below is
                    # whether the resolver let us through at all.

                assert mock_target.called, (
                    f"{func.__name__}(creds=creds) never reached the mocked "
                    f"downstream handler — the resolver rejected the call "
                    f"before any network/enhanced-layer code ran. This is "
                    f"the rc4 regression."
                )

                session_warnings = [
                    x
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                    and "session" in str(x.message).lower()
                ]
                assert session_warnings == [], (
                    f"{func.__name__}(creds=creds) should NOT emit a session "
                    f"deprecation; got: {[str(w.message) for w in session_warnings]}"
                )

    def test_nothing_passed_still_raises(self):
        """Truly missing credentials — no positional, no kwarg — must raise."""
        from ffiec_data_connect.methods import collect_reporting_periods

        with pytest.raises((ValidationError, ValueError)) as exc_info:
            collect_reporting_periods()
        # The error mentions the `creds` field and OAuth2Credentials guidance
        # regardless of legacy-mode wrapping.
        msg = str(exc_info.value)
        assert "creds" in msg and "OAuth2Credentials" in msg

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_pure_kwarg_soap_creds_raises(self, func, patch_target, kwargs):
        """(E3) ``func(creds=soap_creds, ...)`` must raise SOAPDeprecationError.

        This is the exact path the rc5 resolver fix added. Missing rc4
        coverage here is what let the earlier regression slip through, so it
        gets a parametrized pass across every public method.
        """
        soap_creds = Mock(spec=WebserviceCredentials)

        with pytest.raises(SOAPDeprecationError):
            func(creds=soap_creds, **kwargs)

    def test_creds_none_kwarg_raises_validation_error(self):
        """(V2) ``func(creds=None, ...)`` — common user mistake (forgot to
        instantiate creds). Must raise a clear ValidationError, not a confusing
        downstream crash.
        """
        from ffiec_data_connect.methods import collect_reporting_periods

        with pytest.raises((ValidationError, ValueError)) as exc_info:
            collect_reporting_periods(creds=None, series="call")
        msg = str(exc_info.value)
        assert "creds" in msg and "OAuth2Credentials" in msg

    def test_positional_none_only_raises_validation_error(self):
        """(V3) ``func(None)`` — positional None with no creds kwarg.

        Symmetric with V1/V2; distinguishes "nothing at all" from "legacy
        session=None but forgot creds".
        """
        from ffiec_data_connect.methods import collect_reporting_periods

        with warnings.catch_warnings():
            # Positional-None is the deprecated session-positional form; the
            # warning will fire on any success path but we expect failure here.
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises((ValidationError, ValueError)) as exc_info:
                collect_reporting_periods(None, series="call")
        msg = str(exc_info.value)
        # Second arg is default None → "Invalid credentials type" branch.
        assert "credential" in msg.lower() or "OAuth2Credentials" in msg


class TestMixedKwargCombinations:
    """
    Mid-migration and unusual call shapes that aren't covered by the "clean
    pattern" test classes. Each shape is something a real user might write
    while migrating from 2.x. See the rc5 audit plan for the full matrix.
    """

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_positional_none_with_kwarg_creds_warns_and_succeeds(
        self, func, patch_target, kwargs
    ):
        """(S4) ``func(None, creds=creds, ...)`` — half-migrated user.

        Dropped the positional creds but kept the leading ``None``. Should
        emit the positional-``session=None`` deprecation warning and succeed.
        """
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
                    func(None, creds=creds, **kwargs)
                except TypeError as e:
                    pytest.fail(
                        f"{func.__name__}(None, creds=creds) raised TypeError: {e}"
                    )
                except ValueError as e:
                    if "Missing credentials" in str(e):
                        pytest.fail(
                            f"{func.__name__}(None, creds=creds) incorrectly raised: {e}"
                        )
                except Exception:
                    pass

                deprecations = [
                    x
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                    and "session" in str(x.message).lower()
                ]
                assert len(deprecations) >= 1, (
                    f"{func.__name__}(None, creds=creds) should emit a "
                    "session-related DeprecationWarning"
                )

    @pytest.mark.parametrize(
        "func,patch_target,kwargs", METHOD_CONFIGS, ids=_method_ids()
    )
    def test_positional_creds_with_session_none_kwarg_warns(
        self, func, patch_target, kwargs
    ):
        """(S6) ``func(creds, session=None, ...)`` — mid-migration user.

        Moved creds to the first positional slot but hasn't yet removed the
        now-redundant ``session=None``. Should emit the session-kwarg
        deprecation and return the positional creds successfully.
        """
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
                    func(creds, session=None, **kwargs)
                except TypeError as e:
                    pytest.fail(
                        f"{func.__name__}(creds, session=None) raised TypeError: {e}"
                    )
                except Exception:
                    pass

                deprecations = [
                    x
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                    and "session" in str(x.message).lower()
                ]
                assert len(deprecations) >= 1, (
                    f"{func.__name__}(creds, session=None) should emit a "
                    "session-related DeprecationWarning"
                )

    def test_positional_creds_with_truthy_session_currently_discards(self):
        """Documents current behavior of ``func(creds, session=<truthy>, ...)``.

        A valid positional OAuth2Credentials + a truthy (non-None) session
        kwarg currently returns the creds with a session-kwarg deprecation
        warning; the session value is silently discarded.

        The positional equivalent ``func(conn, creds)`` raises
        ``SOAPDeprecationError``, so these probably ought to match — but
        changing the behavior is a semantic shift, not a hotfix. This test
        pins the current behavior so any future change is deliberate.

        See the rc5 audit plan ("Open behavioral question") for context.
        """
        from ffiec_data_connect.methods import collect_reporting_periods

        creds = _make_creds()

        with patch(
            "ffiec_data_connect.methods_enhanced.collect_reporting_periods_enhanced"
        ) as mock_enhanced:
            mock_enhanced.return_value = []

            with pytest.warns(DeprecationWarning, match="session"):
                result = collect_reporting_periods(
                    creds, session="fake_conn_object", series="call"
                )

        # Current rc5 behavior: returns a result (the truthy session is
        # silently discarded). If/when this is changed to raise
        # SOAPDeprecationError for consistency with the positional form,
        # update this test to match.
        assert result is not None


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
                assert (
                    len(deprecation_warnings) >= 1
                ), f"{func.__name__}: expected DeprecationWarning about session kwarg"

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
        assert (
            len(deprecations) >= 1
        ), f"{func.__name__}: expected DeprecationWarning about output_type='bytes'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
