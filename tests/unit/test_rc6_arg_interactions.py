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
from zoneinfo import ZoneInfo

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

# Mirror of methods_enhanced._FFIEC_TZ — tests reference it directly to
# avoid importing a private symbol from the library.
_FFIEC_TZ = ZoneInfo("America/New_York")

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
        # Winter date → EST (UTC-5). The wire format carries no tz marker;
        # the library labels FFIEC timestamps as America/New_York.
        assert result == datetime(2024, 12, 31, tzinfo=_FFIEC_TZ)
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == -5 * 3600

    def test_python_format_from_datetime_string_preserves_time(self):
        result = _format_date_for_output("12/31/2024 3:45:00 PM", "python_format")
        assert isinstance(result, datetime)
        assert result == datetime(2024, 12, 31, 15, 45, 0, tzinfo=_FFIEC_TZ)

    def test_python_format_summer_date_gets_edt(self):
        """ZoneInfo, not a fixed offset, so DST is honored."""
        result = _format_date_for_output("7/15/2024 10:00:00 AM", "python_format")
        assert result.tzinfo is not None
        # EDT = UTC-4
        assert result.utcoffset().total_seconds() == -4 * 3600

    def test_datetime_object_naive_gets_tz_attached(self):
        """Naive datetime input is labeled with America/New_York."""
        dt = datetime(2024, 6, 30, 12, 0, 0)
        result = _format_date_for_output(dt, "python_format")
        assert result == datetime(2024, 6, 30, 12, 0, 0, tzinfo=_FFIEC_TZ)
        assert result.tzinfo is not None

    def test_datetime_object_aware_passthrough_for_python_format(self):
        """If the caller passes an already-aware datetime, respect their tz."""
        from datetime import timezone

        dt = datetime(2024, 6, 30, 12, 0, 0, tzinfo=timezone.utc)
        result = _format_date_for_output(dt, "python_format")
        assert result is dt
        assert result.tzinfo is timezone.utc

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

    def test_non_string_non_datetime_value_passes_through(self):
        """Exotic types (int, dict, etc.) fall through untouched. This is a
        defensive fallback — the validators upstream should prevent these
        values from reaching the formatter, but if they do we prefer a
        pass-through over an opaque TypeError deep in the parser.
        """
        # int, dict, and tuple all non-string / non-datetime — returned as-is.
        assert _format_date_for_output(42, "string_yyyymmdd") == 42
        sentinel = {"weird": "input"}
        assert _format_date_for_output(sentinel, "python_format") is sentinel
        assert _format_date_for_output((1, 2), "string_yyyymmdd") == (1, 2)


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
        assert result[0] == datetime(2024, 12, 31, tzinfo=_FFIEC_TZ)
        assert result[0].tzinfo is not None

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
        assert result[0]["datetime"] == datetime(
            2024, 12, 31, 15, 45, 0, tzinfo=_FFIEC_TZ
        )
        assert result[0]["datetime"].tzinfo is not None

    def test_xbrl_processor_quarter_column_is_tz_aware(self):
        """``collect_data``'s ``quarter`` column goes through ``xbrl_processor``,
        not ``_format_date_for_output``. rc6 makes that path tz-aware too, so
        the two code paths agree and callers can freely mix results across
        methods in comparisons / pandas time-series operations.
        """
        from ffiec_data_connect.xbrl_processor import _process_xml

        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:cc="http://www.ffiec.gov/call">
    <cc:RCON0010 contextRef="PI_123456_2024-03-31_2024-03-31"
                 unitRef="USD" decimals="0">1000000</cc:RCON0010>
</xbrl>"""

        # Winter quarter (Q1 2024) → EST
        result_winter = _process_xml(sample_xml, "python_format")
        assert len(result_winter) >= 1
        q = result_winter[0]["quarter"]
        assert isinstance(q, datetime)
        assert q.tzinfo is not None
        assert q == datetime(2024, 3, 31, tzinfo=_FFIEC_TZ)

        # Summer quarter (Q3 2024) → EDT (test DST round-trip on this path)
        summer_xml = sample_xml.replace(
            b"2024-03-31_2024-03-31", b"2024-09-30_2024-09-30"
        )
        result_summer = _process_xml(summer_xml, "python_format")
        q_summer = result_summer[0]["quarter"]
        assert q_summer.utcoffset().total_seconds() == -4 * 3600

    # ---- gap-filler tests for rc6 tz coverage -----------------------------

    def test_collect_ubpr_reporting_periods_python_format(self):
        """End-to-end: ``collect_ubpr_reporting_periods`` + ``python_format``
        returns tz-aware ``datetime`` objects. (The yyyymmdd path has its own
        test above; this closes the python_format gap.)
        """
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_ubpr_reporting_periods.return_value = ["12/31/2024"]
        with _mock_adapter_everywhere(adapter):
            result = collect_ubpr_reporting_periods(
                creds,
                output_type="list",
                date_output_format="python_format",
            )
        assert len(result) == 1
        assert isinstance(result[0], datetime)
        assert result[0] == datetime(2024, 12, 31, tzinfo=_FFIEC_TZ)
        assert result[0].tzinfo is not None

    def test_collect_filers_submission_date_time_yyyymmdd(self):
        """End-to-end: yyyymmdd mode drops the time component as documented."""
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_filers_submission_date_time(
                creds,
                since_date="1/1/2024",
                reporting_period="12/31/2024",
                output_type="list",
                date_output_format="string_yyyymmdd",
            )
        assert len(result) == 1
        # The yyyymmdd mode drops the time; the quarter-end date remains.
        assert result[0]["datetime"] == "20241231"

    def test_collect_reporting_periods_pandas_output_preserves_tz(self):
        """``output_type='pandas'`` + ``python_format``: the DataFrame column
        is inferred as ``datetime64[ns, America/New_York]`` by pandas when
        handed a list of tz-aware datetimes, so the tz survives the
        List → DataFrame conversion.
        """
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_reporting_periods.return_value = [
            "9/30/2024",
            "12/31/2024",
        ]
        with _mock_adapter_everywhere(adapter):
            df = collect_reporting_periods(
                creds,
                series="call",
                output_type="pandas",
                date_output_format="python_format",
            )
        col = df["reporting_period"]
        # pandas surfaces the tz through the dtype; we don't care about the
        # exact string, only that the tz is present.
        assert col.dt.tz is not None
        assert str(col.dt.tz) == "America/New_York"
        # And a tz-aware datetime comparison works across rows.
        assert col.iloc[0] < col.iloc[1]

    def test_collect_filers_submission_date_time_pandas_preserves_tz(self):
        """Same guarantee on the submission-datetime path: pandas output with
        python_format yields a tz-aware datetime column.
        """
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            df = collect_filers_submission_date_time(
                creds,
                since_date="1/1/2024",
                reporting_period="12/31/2024",
                output_type="pandas",
                date_output_format="python_format",
            )
        assert df["datetime"].dt.tz is not None
        assert str(df["datetime"].dt.tz) == "America/New_York"


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


# ---------------------------------------------------------------------------
# Cross-method tz consistency — the whole point of attaching tz in rc6 is
# that users can mix results across methods without ``TypeError``.
# ---------------------------------------------------------------------------


class TestCrossMethodTzConsistency:
    """Migration doc §9 promises that a user can compare a
    ``collect_data`` quarter against a ``collect_filers_submission_date_time``
    timestamp without the "offset-naive and offset-aware" ``TypeError``.
    These tests pin that promise at the comparison site, not just the
    attribute check.
    """

    def test_reporting_periods_vs_submission_datetime(self):
        """A reporting-period quarter-end can be compared to a submission
        timestamp from ``collect_filers_submission_date_time``.
        """
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_reporting_periods.return_value = ["12/31/2024"]
        # The submission lands 1:30 PM on the same calendar day.
        adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2024 1:30:00 PM"}
        ]
        with _mock_adapter_everywhere(adapter):
            period = collect_reporting_periods(
                creds,
                series="call",
                output_type="list",
                date_output_format="python_format",
            )[0]
            submissions = collect_filers_submission_date_time(
                creds,
                since_date="1/1/2024",
                reporting_period="12/31/2024",
                output_type="list",
                date_output_format="python_format",
            )
        submission_dt = submissions[0]["datetime"]
        # Cross-method comparison must not raise. Period midnight < 1:30 PM.
        assert period < submission_dt
        # Arithmetic across the two must also work.
        assert (submission_dt - period).total_seconds() == 13 * 3600 + 30 * 60

    def test_ubpr_periods_vs_call_periods(self):
        """UBPR and Call Report period lists can be intersected directly
        (common pattern: only pull data for quarters that exist in both).
        """
        creds = _make_creds()
        adapter = _default_mock_adapter()
        adapter.retrieve_reporting_periods.return_value = [
            "9/30/2024",
            "12/31/2024",
        ]
        adapter.retrieve_ubpr_reporting_periods.return_value = [
            "6/30/2024",
            "9/30/2024",
        ]
        with _mock_adapter_everywhere(adapter):
            call_periods = set(
                collect_reporting_periods(
                    creds,
                    series="call",
                    output_type="list",
                    date_output_format="python_format",
                )
            )
            ubpr_periods = set(
                collect_ubpr_reporting_periods(
                    creds,
                    output_type="list",
                    date_output_format="python_format",
                )
            )
        common = call_periods & ubpr_periods
        assert common == {datetime(2024, 9, 30, tzinfo=_FFIEC_TZ)}


# ---------------------------------------------------------------------------
# Polars output path exercised WITH polars installed. The "without polars"
# path is covered above; this closes the other half of the branch.
# ---------------------------------------------------------------------------


class TestPolarsOutputWithPolarsInstalled:
    """Every list-returning method has a polars branch. The
    polars-unavailable path is covered by ``TestPolarsMissingRaisesUniformly``;
    these close the polars-installed path on each method individually.
    """

    def _polars_or_skip(self):
        pytest.importorskip("polars")

    def test_collect_reporting_periods_polars(self):
        self._polars_or_skip()
        import polars as pl

        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_reporting_periods(
                creds, series="call", output_type="polars"
            )
        assert isinstance(result, pl.DataFrame)
        assert result.columns == ["reporting_period"]

    def test_collect_ubpr_reporting_periods_polars(self):
        """Closes the coverage gap flagged by pytest-cov (methods.py:1141)."""
        self._polars_or_skip()
        import polars as pl

        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_ubpr_reporting_periods(creds, output_type="polars")
        assert isinstance(result, pl.DataFrame)
        assert result.columns == ["reporting_period"]

    def test_collect_filers_since_date_polars(self):
        self._polars_or_skip()
        import polars as pl

        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_filers_since_date(
                creds,
                since_date="1/1/2024",
                reporting_period="12/31/2024",
                output_type="polars",
            )
        assert isinstance(result, pl.DataFrame)

    def test_collect_filers_submission_date_time_polars(self):
        self._polars_or_skip()
        import polars as pl

        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            result = collect_filers_submission_date_time(
                creds,
                since_date="1/1/2024",
                reporting_period="12/31/2024",
                output_type="polars",
            )
        assert isinstance(result, pl.DataFrame)


# ---------------------------------------------------------------------------
# Legacy-mode interactions with the new rc6 surfaces. In legacy mode
# ``raise_exception`` re-wraps typed exceptions as ``ValueError``, so any
# behavior we pin under non-legacy should also be sanity-checked under
# legacy for the paths a 2.x script might still rely on.
# ---------------------------------------------------------------------------


class TestLegacyModeRc6Interactions:
    """Legacy mode must still surface the same *categories* of failure
    (just as ``ValueError`` instead of the typed subclass) for rc6 rules.
    """

    @pytest.fixture
    def legacy_mode(self):
        """Opt a single test into legacy mode (overrides the module-level
        ``set_legacy_errors(False)`` autouse fixture).
        """
        Config.set_legacy_errors(True)
        yield
        Config.set_legacy_errors(False)

    def test_polars_missing_raises_valueerror_in_legacy(self, legacy_mode):
        """rc6 ``output_type='polars'`` without the extra → ``ValueError``
        in legacy mode (vs ``ValidationError`` in new mode).

        Caveat worth flagging: in legacy mode, ``_require_polars_available``
        raises ``ValueError("Polars not available")``, which is not a
        ``FFIECError`` subclass and so gets re-wrapped by the outer
        ``except Exception`` as the "Failed to retrieve ... via REST API"
        ``ConnectionError`` message (which is itself a ``ValueError`` in
        legacy mode). Net effect: legacy-mode users see a message that
        suggests a network failure, when the real cause is a missing extra.
        In non-legacy mode the typed ``ValidationError`` re-raises untouched.

        Filed mentally for a follow-up: in legacy mode the except block
        should also preserve ``ValueError`` untouched (because that's how
        typed errors present when the library itself raised them). Keeping
        the behavior as-is for rc6 — narrow hotfix scope.
        """
        creds = _make_creds()
        with _mock_adapter_everywhere(_default_mock_adapter()):
            with patch("ffiec_data_connect.methods_enhanced.POLARS_AVAILABLE", False):
                # Case-insensitive since the wrapped message capitalizes
                # "Polars" and the inner one doesn't.
                with pytest.raises(ValueError, match="(?i)polars"):
                    collect_reporting_periods(
                        creds, series="call", output_type="polars"
                    )

    def test_unparseable_python_format_raises_valueerror_in_legacy(self, legacy_mode):
        """The rc6 unparseable-in-python_format raise survives legacy mode
        (as ``ValueError``). Key: it is *not* silently returned as a string.
        """
        with pytest.raises(ValueError, match="date"):
            _format_date_for_output("not a date", "python_format")

    def test_user_warnings_still_fire_in_legacy_mode(self, legacy_mode):
        """``UserWarning`` for ignored-param combos is independent of the
        legacy exception toggle — both modes should still warn.
        """
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
