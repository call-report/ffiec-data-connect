"""
Live integration tests for the FFIEC REST API.

Requires environment variables:
    FFIEC_USERNAME      - FFIEC portal username
    FFIEC_BEARER_TOKEN  - 90-day JWT bearer token

Run:
    FFIEC_USERNAME=... FFIEC_BEARER_TOKEN='eyJ...' pytest tests/integration/test_rest_api_live.py -v

These tests hit the real FFIEC API. They are skipped automatically
when credentials are not provided.
"""

import os
from datetime import datetime

import pandas as pd
import pytest

from ffiec_data_connect import (
    OAuth2Credentials,
    SOAPDeprecationError,
    collect_data,
    collect_filers_on_reporting_period,
    collect_filers_since_date,
    collect_filers_submission_date_time,
    collect_reporting_periods,
    collect_ubpr_facsimile_data,
    collect_ubpr_reporting_periods,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_creds():
    """Provide live OAuth2Credentials from environment, or skip."""
    username = os.environ.get("FFIEC_USERNAME")
    token = os.environ.get("FFIEC_BEARER_TOKEN")
    if not username or not token:
        pytest.skip("Set FFIEC_USERNAME and FFIEC_BEARER_TOKEN to run live tests")
    creds = OAuth2Credentials(username=username, bearer_token=token)
    if creds.is_expired:
        pytest.skip(f"Token expired on {creds.token_expires}")
    return creds


# A known reporting period and RSSD for reproducible tests
REPORTING_PERIOD = "12/31/2024"
RSSD_ID = "480228"  # JPMorgan Chase


# ---------------------------------------------------------------------------
# collect_reporting_periods
# ---------------------------------------------------------------------------


class TestCollectReportingPeriods:
    """Test collect_reporting_periods against the live API."""

    def test_call_series_list(self, live_creds):
        periods = collect_reporting_periods(
            live_creds, series="call", output_type="list"
        )
        assert isinstance(periods, list)
        assert len(periods) > 0
        # Should be date strings
        assert "/" in periods[0]

    def test_call_series_sorted_ascending(self, live_creds):
        periods = collect_reporting_periods(
            live_creds, series="call", output_type="list"
        )
        # Oldest first
        assert periods == sorted(
            periods, key=lambda d: datetime.strptime(d, "%m/%d/%Y")
        )

    def test_call_series_pandas(self, live_creds):
        result = collect_reporting_periods(
            live_creds, series="call", output_type="pandas"
        )
        assert isinstance(result, pd.DataFrame)
        assert "reporting_period" in result.columns
        assert len(result) > 0

    def test_ubpr_series(self, live_creds):
        periods = collect_reporting_periods(
            live_creds, series="ubpr", output_type="list"
        )
        assert isinstance(periods, list)
        assert len(periods) > 0

    @pytest.mark.xfail(
        reason="date_output_format not yet implemented in REST enhanced path"
    )
    def test_date_format_yyyymmdd(self, live_creds):
        periods = collect_reporting_periods(
            live_creds,
            series="call",
            output_type="list",
            date_output_format="string_yyyymmdd",
        )
        assert isinstance(periods, list)
        # Should be YYYYMMDD format
        assert len(periods[0]) == 8
        assert periods[0].isdigit()

    @pytest.mark.xfail(
        reason="date_output_format not yet implemented in REST enhanced path"
    )
    def test_date_format_python(self, live_creds):
        periods = collect_reporting_periods(
            live_creds,
            series="call",
            output_type="list",
            date_output_format="python_format",
        )
        assert isinstance(periods, list)
        assert isinstance(periods[0], datetime)


# ---------------------------------------------------------------------------
# collect_data
# ---------------------------------------------------------------------------


class TestCollectData:
    """Test collect_data (RetrieveFacsimile) against the live API."""

    def test_call_series_list(self, live_creds):
        data = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="list",
        )
        assert isinstance(data, list)
        assert len(data) > 0
        row = data[0]
        assert "mdrm" in row
        assert "rssd" in row

    def test_call_series_pandas(self, live_creds):
        df = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="pandas",
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "mdrm" in df.columns
        assert "rssd" in df.columns

    def test_force_null_pandas(self, live_creds):
        df = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="pandas",
            force_null_types="pandas",
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_force_null_numpy(self, live_creds):
        df = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="pandas",
            force_null_types="numpy",
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_various_date_formats(self, live_creds):
        """Multiple date input formats should work."""
        for date_fmt in ["12/31/2024", "2024-12-31"]:
            data = collect_data(
                live_creds,
                reporting_period=date_fmt,
                rssd_id=RSSD_ID,
                series="call",
                output_type="list",
            )
            assert len(data) > 0, f"No data for date format: {date_fmt}"

    def test_datetime_input(self, live_creds):
        data = collect_data(
            live_creds,
            reporting_period=datetime(2024, 12, 31),
            rssd_id=RSSD_ID,
            series="call",
            output_type="list",
        )
        assert len(data) > 0


# ---------------------------------------------------------------------------
# collect_filers_on_reporting_period
# ---------------------------------------------------------------------------


class TestCollectFilersOnReportingPeriod:
    """Test collect_filers_on_reporting_period (PanelOfReporters)."""

    def test_list_output(self, live_creds):
        filers = collect_filers_on_reporting_period(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            output_type="list",
        )
        assert isinstance(filers, list)
        assert len(filers) > 100  # thousands of banks file
        row = filers[0]
        # Dual field names
        assert "rssd" in row
        assert "id_rssd" in row
        assert row["rssd"] == row["id_rssd"]
        # Other normalized fields
        assert "name" in row
        assert "zip" in row

    def test_pandas_output(self, live_creds):
        df = collect_filers_on_reporting_period(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            output_type="pandas",
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 100
        assert "rssd" in df.columns
        assert "id_rssd" in df.columns

    def test_zip_codes_are_strings(self, live_creds):
        """ZIP codes should be strings (5-digit or ZIP+4)."""
        filers = collect_filers_on_reporting_period(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            output_type="list",
        )
        for filer in filers[:50]:
            if filer.get("zip") and filer["zip"] != "00000":
                assert isinstance(filer["zip"], str), f"ZIP not string: {filer['zip']}"
                assert len(filer["zip"]) >= 5, f"ZIP too short: {filer['zip']}"


# ---------------------------------------------------------------------------
# collect_filers_since_date
# ---------------------------------------------------------------------------


class TestCollectFilersSinceDate:
    """Test collect_filers_since_date (FilersSinceDate)."""

    def test_list_output(self, live_creds):
        filers = collect_filers_since_date(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            since_date="1/1/2024",
            output_type="list",
        )
        assert isinstance(filers, list)
        assert len(filers) > 0
        # Should be RSSD ID strings
        assert isinstance(filers[0], str)

    def test_pandas_output(self, live_creds):
        result = collect_filers_since_date(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            since_date="1/1/2024",
            output_type="pandas",
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# collect_filers_submission_date_time
# ---------------------------------------------------------------------------


class TestCollectFilersSubmissionDateTime:
    """Test collect_filers_submission_date_time."""

    def test_list_output(self, live_creds):
        submissions = collect_filers_submission_date_time(
            live_creds,
            since_date="1/1/2024",
            reporting_period=REPORTING_PERIOD,
            output_type="list",
        )
        assert isinstance(submissions, list)
        assert len(submissions) > 0
        row = submissions[0]
        assert "rssd" in row
        assert "id_rssd" in row
        assert "datetime" in row
        assert row["rssd"] == row["id_rssd"]

    def test_pandas_output(self, live_creds):
        df = collect_filers_submission_date_time(
            live_creds,
            since_date="1/1/2024",
            reporting_period=REPORTING_PERIOD,
            output_type="pandas",
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "rssd" in df.columns
        assert "id_rssd" in df.columns


# ---------------------------------------------------------------------------
# collect_ubpr_reporting_periods
# ---------------------------------------------------------------------------


class TestCollectUBPRReportingPeriods:
    """Test collect_ubpr_reporting_periods (REST-only endpoint)."""

    def test_list_output(self, live_creds):
        periods = collect_ubpr_reporting_periods(live_creds, output_type="list")
        assert isinstance(periods, list)
        assert len(periods) > 0

    def test_pandas_output(self, live_creds):
        result = collect_ubpr_reporting_periods(live_creds, output_type="pandas")
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# collect_ubpr_facsimile_data
# ---------------------------------------------------------------------------


class TestCollectUBPRFacsimileData:
    """Test collect_ubpr_facsimile_data (REST-only endpoint)."""

    def test_list_output(self, live_creds):
        data = collect_ubpr_facsimile_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            output_type="list",
        )
        assert isinstance(data, (list, bytes))
        if isinstance(data, list):
            assert len(data) > 0

    @pytest.mark.filterwarnings("ignore::FutureWarning")
    def test_pandas_output(self, live_creds):
        result = collect_ubpr_facsimile_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            output_type="pandas",
        )
        assert isinstance(result, (pd.DataFrame, bytes))


# ---------------------------------------------------------------------------
# SOAP deprecation (no credentials needed)
# ---------------------------------------------------------------------------


class TestSOAPDeprecationLive:
    """Verify SOAP classes raise even when credentials are available."""

    def test_session_not_none_raises(self, live_creds):
        """Passing a non-None session should raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            collect_reporting_periods("ignored", live_creds, series="call")


# ---------------------------------------------------------------------------
# Credential validation
# ---------------------------------------------------------------------------


class TestCredentialValidation:
    """Test credential behavior with live tokens."""

    def test_token_expiry_auto_detected(self, live_creds):
        """JWT exp claim should be automatically extracted."""
        assert live_creds.token_expires is not None
        assert isinstance(live_creds.token_expires, datetime)

    def test_token_not_expired(self, live_creds):
        """The token used for testing should not be expired."""
        assert not live_creds.is_expired


# ---------------------------------------------------------------------------
# Output type coverage: polars (backfill) + xbrl / pdf (new in 3.0.0rc4)
# ---------------------------------------------------------------------------

try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:  # pragma: no cover
    POLARS_AVAILABLE = False
    pl = None  # type: ignore


@pytest.mark.skipif(not POLARS_AVAILABLE, reason="polars not installed")
class TestOutputTypePolars:
    """Backfill: no prior live coverage for output_type='polars'.

    One test per method. Each asserts the result is a ``polars.DataFrame``
    (or list of strings for endpoints that don't tabulate).
    """

    def test_collect_reporting_periods_polars(self, live_creds):
        result = collect_reporting_periods(
            live_creds, series="call", output_type="polars"
        )
        # Endpoint returns a list even with output_type='polars' — the enhanced
        # path only hits polars when there are tabular columns. Accept either.
        assert isinstance(result, (pl.DataFrame, list))

    def test_collect_data_polars(self, live_creds):
        result = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="polars",
        )
        assert isinstance(result, pl.DataFrame)
        assert result.height > 0

    def test_collect_filers_since_date_polars(self, live_creds):
        result = collect_filers_since_date(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            since_date="1/1/2024",
            output_type="polars",
        )
        assert isinstance(result, (pl.DataFrame, list))

    def test_collect_filers_submission_date_time_polars(self, live_creds):
        result = collect_filers_submission_date_time(
            live_creds,
            since_date="1/1/2024",
            reporting_period=REPORTING_PERIOD,
            output_type="polars",
        )
        assert isinstance(result, (pl.DataFrame, list))

    def test_collect_filers_on_reporting_period_polars(self, live_creds):
        result = collect_filers_on_reporting_period(
            live_creds, reporting_period=REPORTING_PERIOD, output_type="polars"
        )
        assert isinstance(result, (pl.DataFrame, list))

    def test_collect_ubpr_reporting_periods_polars(self, live_creds):
        result = collect_ubpr_reporting_periods(live_creds, output_type="polars")
        assert isinstance(result, (pl.DataFrame, list))

    def test_collect_ubpr_facsimile_data_polars(self, live_creds):
        result = collect_ubpr_facsimile_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            output_type="polars",
        )
        # Facsimile endpoints may return bytes for unhandled output_types — but
        # for polars specifically the method should produce a DataFrame.
        assert isinstance(result, (pl.DataFrame, list, bytes))


class TestOutputTypeXbrlAndPdf:
    """Live coverage for the new xbrl / pdf output_types in 3.0.0rc4."""

    def test_collect_data_xbrl_returns_xml_bytes(self, live_creds):
        """xbrl output on collect_data returns raw XBRL XML bytes."""
        result = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="xbrl",
        )
        assert isinstance(result, bytes)
        assert result.startswith(
            b"<?xml"
        ), f"Expected a clean '<?xml' prolog (no BOM), got first 16 bytes: {result[:16]!r}"

    def test_collect_ubpr_facsimile_xbrl_returns_xml_bytes(self, live_creds):
        """xbrl output on collect_ubpr_facsimile_data returns raw XBRL XML bytes.

        Both facsimile endpoints produce a consistent shape: raw UTF-8 XBRL
        bytes beginning with ``<?xml`` — the adapter normalizes the UBPR
        response's UTF-8 BOM away so callers never see it.
        """
        result = collect_ubpr_facsimile_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            output_type="xbrl",
        )
        assert isinstance(result, bytes)
        assert result.startswith(
            b"<?xml"
        ), f"Expected a clean '<?xml' prolog (no BOM), got first 16 bytes: {result[:16]!r}"

    def test_collect_data_pdf_returns_pdf_bytes(self, live_creds):
        """pdf output on collect_data returns PDF bytes. Depends on FFIEC server support."""
        result = collect_data(
            live_creds,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="pdf",
        )
        assert isinstance(result, bytes)
        assert result.startswith(
            b"%PDF"
        ), f"Expected PDF magic bytes, got: {result[:20]!r}"

    def test_collect_data_ubpr_pdf_raises_validation_error(self, live_creds):
        """PDF for UBPR series must raise locally — no network call."""
        from ffiec_data_connect.exceptions import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            collect_data(
                live_creds,
                reporting_period=REPORTING_PERIOD,
                rssd_id=RSSD_ID,
                series="ubpr",
                output_type="pdf",
            )


class TestOutputTypeBytesDeprecationLive:
    """Verify the 'bytes' deprecation path behaves correctly end-to-end.

    ``bytes`` is deprecated in 3.0.0rc4 — still works on
    collect_ubpr_facsimile_data (translated to xbrl + warns), raises on every
    other method.
    """

    def test_bytes_on_ubpr_facsimile_warns_and_returns_bytes(self, live_creds):
        import warnings

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            result = collect_ubpr_facsimile_data(
                live_creds,
                reporting_period=REPORTING_PERIOD,
                rssd_id=RSSD_ID,
                output_type="bytes",
            )

        assert isinstance(result, bytes)
        deprecations = [
            w
            for w in captured
            if issubclass(w.category, DeprecationWarning)
            and "bytes" in str(w.message).lower()
        ]
        assert (
            len(deprecations) >= 1
        ), "Expected DeprecationWarning about output_type='bytes'"

    def test_bytes_on_reporting_periods_raises(self, live_creds):
        """output_type='bytes' must raise on non-facsimile methods (local validation)."""
        from ffiec_data_connect.exceptions import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            collect_reporting_periods(live_creds, series="call", output_type="bytes")
