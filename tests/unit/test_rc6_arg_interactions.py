"""
rc6 tests: argument-interaction correctness.

Covers five pieces of rc6 work:

- **A+B** ``UserWarning`` when ``force_null_types`` / ``date_output_format``
  are passed with a raw-bytes ``output_type`` (``"xbrl"`` or ``"pdf"``) on
  ``collect_data`` and ``collect_ubpr_facsimile_data``.
- **C** ``output_type="polars"`` raises ``ValidationError`` on every method
  when polars isn't installed (previously silently fell back to list in the
  enhanced layer, inconsistent with ``collect_data``).
- **D1** ``date_output_format`` is now honored on
  ``collect_reporting_periods``, ``collect_ubpr_reporting_periods``, and
  ``collect_filers_submission_date_time``. Tests cover the shared
  ``_format_date_for_output`` helper and end-to-end wiring.
- **E** Stale "endpoint may not be implemented" error text was replaced
  with accurate "transient upstream" wording.
- **F** ``UserWarning`` when ``force_null_types`` is passed to a method
  whose return has no typed null columns.
"""

import warnings
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from ffiec_data_connect.config import Config
from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.exceptions import ValidationError
from ffiec_data_connect.methods import (
    collect_data,
    collect_filers_on_reporting_period,
    collect_filers_since_date,
    collect_filers_submission_date_time,
    collect_reporting_periods,
    collect_ubpr_facsimile_data,
    collect_ubpr_reporting_periods,
)
from ffiec_data_connect.methods_enhanced import (
    _format_date_for_output,
)

TEST_JWT = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
)


@pytest.fixture(autouse=True)
def _disable_legacy_and_suppress_token_warning():
    Config.set_legacy_errors(False)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Bearer token passed directly")
        yield
    Config.reset()


def _make_creds() -> OAuth2Credentials:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Bearer token passed directly")
        return OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)


@contextmanager
def _mock_adapter_everywhere(adapter: Mock):
    """Patch ``create_protocol_adapter`` in BOTH import paths.

    ``methods.py`` function-locally imports from ``protocol_adapter``, while
    ``methods_enhanced.py`` binds the name at module load time. Patching only
    one site lets the other slip through to a real network call, so we patch
    both to intercept every call-path into the adapter layer.
    """
    with patch(
        "ffiec_data_connect.protocol_adapter.create_protocol_adapter",
        return_value=adapter,
    ):
        with patch(
            "ffiec_data_connect.methods_enhanced.create_protocol_adapter",
            return_value=adapter,
        ):
            yield adapter


def _default_mock_adapter() -> Mock:
    """A mock adapter wired for whatever endpoint the test happens to hit."""
    m = Mock()
    m.retrieve_reporting_periods.return_value = ["12/31/2024", "9/30/2024"]
    m.retrieve_ubpr_reporting_periods.return_value = ["12/31/2024", "9/30/2024"]
    m.retrieve_facsimile.return_value = b'<?xml version="1.0"?><xbrl/>'
    m.retrieve_ubpr_xbrl_facsimile.return_value = b'<?xml version="1.0"?><xbrl/>'
    m.retrieve_filers_since_date.return_value = ["480228", "852320"]
    m.retrieve_filers_submission_datetime.return_value = [
        {"ID_RSSD": 480228, "DateTime": "12/31/2024 3:45:00 PM"}
    ]
    m.retrieve_panel_of_reporters.return_value = [
        {"ID_RSSD": 480228, "Name": "Bank", "ZIP": "02886", "State": "RI"}
    ]
    return m


# ---------------------------------------------------------------------------
# A + B: UserWarning when force_null_types / date_output_format are passed
# with a raw-bytes output_type.
# ---------------------------------------------------------------------------


class TestRawBytesIgnoredParamsWarn:
    """Raw-bytes outputs bypass parsing; params that affect parsing warn."""

    def test_collect_data_xbrl_force_null_types_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*has no effect"):
                collect_data(
                    creds,
                    reporting_period="12/31/2024",
                    rssd_id="480228",
                    series="call",
                    output_type="xbrl",
                    force_null_types="pandas",
                )

    def test_collect_data_xbrl_date_output_format_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="date_output_format.*has no effect"):
                collect_data(
                    creds,
                    reporting_period="12/31/2024",
                    rssd_id="480228",
                    series="call",
                    output_type="xbrl",
                    date_output_format="python_format",
                )

    def test_collect_data_pdf_force_null_types_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*has no effect"):
                collect_data(
                    creds,
                    reporting_period="12/31/2024",
                    rssd_id="480228",
                    series="call",
                    output_type="pdf",
                    force_null_types="numpy",
                )

    def test_collect_data_pdf_date_output_format_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="date_output_format.*has no effect"):
                collect_data(
                    creds,
                    reporting_period="12/31/2024",
                    rssd_id="480228",
                    series="call",
                    output_type="pdf",
                    date_output_format="string_yyyymmdd",
                )

    def test_collect_ubpr_facsimile_xbrl_force_null_types_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*has no effect"):
                collect_ubpr_facsimile_data(
                    creds,
                    reporting_period="12/31/2024",
                    rssd_id="480228",
                    output_type="xbrl",
                    force_null_types="pandas",
                )

    # ---- negative cases -------------------------------------------------

    def test_collect_data_xbrl_defaults_no_warning(self):
        """xbrl + default args → no ignored-param warnings."""
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                collect_data(
                    creds,
                    reporting_period="12/31/2024",
                    rssd_id="480228",
                    series="call",
                    output_type="xbrl",
                )
            ignored = [
                w
                for w in captured
                if issubclass(w.category, UserWarning)
                and "has no effect" in str(w.message)
            ]
            assert ignored == []

    def test_collect_data_pandas_force_null_types_no_warning(self):
        """pandas + force_null_types → no warning (force_null_types is honored)."""
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                try:
                    collect_data(
                        creds,
                        reporting_period="12/31/2024",
                        rssd_id="480228",
                        series="call",
                        output_type="pandas",
                        force_null_types="pandas",
                    )
                except Exception:
                    # Minimal mock XBRL may not parse cleanly; we only care
                    # about the warnings emitted up to that point.
                    pass
            ignored = [
                w
                for w in captured
                if issubclass(w.category, UserWarning)
                and "has no effect" in str(w.message)
            ]
            assert ignored == []


# ---------------------------------------------------------------------------
# C: polars requested without polars installed → ValidationError.
# ---------------------------------------------------------------------------


class TestPolarsNotAvailableRaises:
    """``output_type='polars'`` without the polars extra installed must raise
    uniformly, matching ``collect_data``'s existing behavior.
    """

    @pytest.mark.parametrize(
        "func,kwargs",
        [
            (collect_reporting_periods, {"series": "call"}),
            (
                collect_filers_since_date,
                {"reporting_period": "12/31/2024", "since_date": "1/1/2024"},
            ),
            (
                collect_filers_submission_date_time,
                {"since_date": "1/1/2024", "reporting_period": "12/31/2024"},
            ),
            (collect_filers_on_reporting_period, {"reporting_period": "12/31/2024"}),
            (collect_ubpr_reporting_periods, {}),
        ],
        ids=lambda v: v.__name__ if callable(v) else "kwargs",
    )
    def test_method_raises_when_polars_missing(self, func, kwargs):
        creds = _make_creds()
        with patch("ffiec_data_connect.methods_enhanced.POLARS_AVAILABLE", False):
            with _mock_adapter_everywhere(_default_mock_adapter()):
                with pytest.raises((ValidationError, ValueError), match="polars"):
                    func(creds, output_type="polars", **kwargs)


# ---------------------------------------------------------------------------
# D1: _format_date_for_output helper and end-to-end wiring.
# ---------------------------------------------------------------------------


class TestFormatDateForOutput:
    """Unit tests for the shared date-format helper."""

    def test_string_original_passthrough(self):
        assert _format_date_for_output("12/31/2024", "string_original") == "12/31/2024"
        assert (
            _format_date_for_output("12/31/2024 3:45:00 PM", "string_original")
            == "12/31/2024 3:45:00 PM"
        )

    def test_string_yyyymmdd_from_date(self):
        assert _format_date_for_output("12/31/2024", "string_yyyymmdd") == "20241231"
        assert _format_date_for_output("3/31/2024", "string_yyyymmdd") == "20240331"

    def test_string_yyyymmdd_from_datetime_string_drops_time(self):
        """The time component is dropped; YYYYMMDD is a date format."""
        assert (
            _format_date_for_output("12/31/2024 3:45:00 PM", "string_yyyymmdd")
            == "20241231"
        )

    def test_python_format_from_date(self):
        result = _format_date_for_output("12/31/2024", "python_format")
        assert isinstance(result, datetime)
        assert result == datetime(2024, 12, 31)

    def test_python_format_from_datetime_string_preserves_time(self):
        result = _format_date_for_output("12/31/2024 3:45:00 PM", "python_format")
        assert isinstance(result, datetime)
        assert result == datetime(2024, 12, 31, 15, 45, 0)

    def test_datetime_object_passthrough_for_python_format(self):
        dt = datetime(2024, 6, 30, 12, 0, 0)
        assert _format_date_for_output(dt, "python_format") is dt

    def test_datetime_object_formatted_for_string_yyyymmdd(self):
        dt = datetime(2024, 6, 30, 12, 0, 0)
        assert _format_date_for_output(dt, "string_yyyymmdd") == "20240630"

    def test_empty_string_passthrough(self):
        assert _format_date_for_output("", "string_yyyymmdd") == ""

    def test_none_passthrough(self):
        assert _format_date_for_output(None, "string_yyyymmdd") is None

    def test_unparseable_string_passthrough(self):
        """Garbage input returned unchanged — better than a half-converted result."""
        assert _format_date_for_output("not a date", "string_yyyymmdd") == "not a date"


class TestDateOutputFormatEndToEnd:
    """Each affected collect_* method honors date_output_format end-to-end."""

    def test_collect_reporting_periods_yyyymmdd(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_reporting_periods(
                creds,
                series="call",
                output_type="list",
                date_output_format="string_yyyymmdd",
            )
        assert result == ["20240930", "20241231"]

    def test_collect_reporting_periods_python_format(self):
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_reporting_periods.return_value = ["12/31/2024"]
        with _mock_adapter_everywhere(adapter):
            result = collect_reporting_periods(
                creds,
                series="call",
                output_type="list",
                date_output_format="python_format",
            )
        assert len(result) == 1
        assert isinstance(result[0], datetime)
        assert result[0] == datetime(2024, 12, 31)

    def test_collect_ubpr_reporting_periods_yyyymmdd(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_ubpr_reporting_periods(
                creds,
                output_type="list",
                date_output_format="string_yyyymmdd",
            )
        assert "20241231" in result
        assert "20240930" in result

    def test_collect_filers_submission_date_time_python_format(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_filers_submission_date_time(
                creds,
                since_date="1/1/2024",
                reporting_period="12/31/2024",
                output_type="list",
                date_output_format="python_format",
            )
        assert len(result) == 1
        assert isinstance(result[0]["datetime"], datetime)
        assert result[0]["datetime"] == datetime(2024, 12, 31, 15, 45, 0)


# ---------------------------------------------------------------------------
# E: the new error wording.
# ---------------------------------------------------------------------------


class TestFacsimile500MessageNotStale:
    """The HTTP-500 handler for RetrieveFacsimile used to say the endpoint
    "may not be implemented yet" — now talks about transient upstream issues.
    """

    def test_protocol_adapter_500_message_updated(self):
        import inspect

        import ffiec_data_connect.protocol_adapter as pa

        source = inspect.getsource(pa.RESTAdapter.retrieve_facsimile)
        assert "may not be implemented yet" not in source
        assert "transient" in source.lower()

    def test_methods_500_log_message_updated(self):
        import inspect

        import ffiec_data_connect.methods as m

        source = inspect.getsource(m.collect_data)
        assert "may not be fully implemented yet" not in source
        assert "transient" in source.lower() or "retry" in source.lower()


# ---------------------------------------------------------------------------
# F: force_null_types with list-of-strings methods emits UserWarning.
# ---------------------------------------------------------------------------


class TestForceNullTypesNoOpWarning:
    """Three methods accept force_null_types for API symmetry but truly do
    nothing with it. Warn the user so they don't assume it's working.
    """

    def test_collect_reporting_periods_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*no effect"):
                collect_reporting_periods(
                    creds, series="call", force_null_types="pandas"
                )

    def test_collect_ubpr_reporting_periods_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*no effect"):
                collect_ubpr_reporting_periods(creds, force_null_types="pandas")

    def test_collect_filers_since_date_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*no effect"):
                collect_filers_since_date(
                    creds,
                    reporting_period="12/31/2024",
                    since_date="1/1/2024",
                    force_null_types="pandas",
                )

    def test_no_warning_when_force_null_types_omitted(self):
        """Default (None) must not trigger the warning."""
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                collect_reporting_periods(creds, series="call")
            no_op = [
                w
                for w in captured
                if issubclass(w.category, UserWarning) and "no effect" in str(w.message)
            ]
            assert no_op == []

    # The following two tests address a rc6 review finding: the warning was
    # applied to 3 of the 5 methods that document force_null_types as a
    # no-op. These two were missing; they warn too for symmetry.

    def test_collect_filers_submission_date_time_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*no effect"):
                collect_filers_submission_date_time(
                    creds,
                    since_date="1/1/2024",
                    reporting_period="12/31/2024",
                    force_null_types="pandas",
                )

    def test_collect_filers_on_reporting_period_warns(self):
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with pytest.warns(UserWarning, match="force_null_types.*no effect"):
                collect_filers_on_reporting_period(
                    creds,
                    reporting_period="12/31/2024",
                    force_null_types="pandas",
                )


# ---------------------------------------------------------------------------
# Review follow-ups — `_format_date_for_output` unparseable input handling,
# and propagation of programming errors through the enhanced methods.
# ---------------------------------------------------------------------------


class TestFormatDateUnparseableInput:
    """rc6 review finding: unparseable input must not silently return a str
    when the caller requested ``python_format``, which would violate the
    documented return type and break downstream ``.year`` / ``.month`` access.
    """

    def test_python_format_unparseable_raises(self):
        """python_format + unparseable input → ValidationError."""
        # Matches both legacy ("Cannot parse date ...") and non-legacy
        # ("Validation failed for field 'date_value' ...") message forms.
        with pytest.raises((ValidationError, ValueError), match="date"):
            _format_date_for_output("not a date", "python_format")

    def test_python_format_dashes_raises(self):
        """ISO-ish input (dashes) isn't supported; raises in python_format."""
        # Matches both legacy ("Cannot parse date ...") and non-legacy
        # ("Validation failed for field 'date_value' ...") message forms.
        with pytest.raises((ValidationError, ValueError), match="date"):
            _format_date_for_output("2024-12-31", "python_format")

    def test_string_yyyymmdd_unparseable_passes_through(self):
        """string_yyyymmdd + unparseable input → unchanged (still a string).

        A string return is type-compatible here; caller doesn't expect a
        datetime, so a log-and-passthrough is the safer default.
        """
        assert _format_date_for_output("not a date", "string_yyyymmdd") == "not a date"
        assert _format_date_for_output("2024-12-31", "string_yyyymmdd") == "2024-12-31"


class TestProgrammingErrorsPropagate:
    """rc6 review finding: the narrowed ``except Exception`` in the enhanced
    methods lets ``AttributeError`` / ``KeyError`` / ``TypeError`` bubble
    through untouched. Wrapping those as ``ConnectionError`` misleads users
    into thinking FFIEC is down when the real problem is a library bug or
    API shape drift.
    """

    def test_attribute_error_from_adapter_propagates(self):
        """A raw AttributeError from the adapter is NOT wrapped as ConnectionError."""
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_reporting_periods.side_effect = AttributeError(
            "shape drift: 'NoneType' object has no attribute 'root'"
        )
        with _mock_adapter_everywhere(adapter):
            # Must raise AttributeError, NOT ConnectionError — a shape-drift
            # bug is not a network issue.
            with pytest.raises(AttributeError, match="shape drift"):
                collect_reporting_periods(creds, series="call")

    def test_key_error_from_adapter_propagates(self):
        """A raw KeyError propagates."""
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_filers_since_date.side_effect = KeyError("ID_RSSD")
        with _mock_adapter_everywhere(adapter):
            with pytest.raises(KeyError, match="ID_RSSD"):
                collect_filers_since_date(
                    creds,
                    reporting_period="12/31/2024",
                    since_date="1/1/2024",
                )
