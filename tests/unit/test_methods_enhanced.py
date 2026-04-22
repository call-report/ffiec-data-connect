"""
Unit tests for methods_enhanced.py

Tests enhanced REST API methods by mocking the protocol adapter,
ensuring logic (sorting, normalization, output formatting) works
correctly without live API calls.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from ffiec_data_connect.config import Config
from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.exceptions import ConnectionError, ValidationError
from ffiec_data_connect.methods_enhanced import (
    _format_datetime_for_output,
    _normalize_pydantic_to_soap_format,
    collect_filers_on_reporting_period_enhanced,
    collect_filers_since_date_enhanced,
    collect_filers_submission_date_time_enhanced,
    collect_reporting_periods_enhanced,
)

# Test JWT: {"alg":"none","typ":"JWT"}.{"sub":"test","exp":1783442253} (far future)
TEST_JWT = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
)


@pytest.fixture(autouse=True)
def _disable_legacy_errors():
    """Disable legacy errors so tests get specific exception types."""
    Config.set_legacy_errors(False)
    yield
    Config.reset()


def _make_creds() -> OAuth2Credentials:
    """Create real OAuth2Credentials with a test JWT for use in tests."""
    return OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)


# ---------------------------------------------------------------------------
# collect_reporting_periods_enhanced
# ---------------------------------------------------------------------------
class TestCollectReportingPeriodsEnhanced:
    """Tests for collect_reporting_periods_enhanced."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_returns_sorted_ascending_list(self, mock_create_adapter):
        """Periods should be sorted oldest-first regardless of API order."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = [
            "12/31/2023",
            "6/30/2023",
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="call",
            output_type="list",
            date_output_format="string_original",
        )

        assert isinstance(result, list)
        assert result == ["6/30/2023", "12/31/2023"]

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_returns_pandas_dataframe(self, mock_create_adapter):
        """output_type='pandas' should return a DataFrame with reporting_period column."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = [
            "3/31/2023",
            "12/31/2022",
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="call",
            output_type="pandas",
            date_output_format="string_original",
        )

        assert isinstance(result, pd.DataFrame)
        assert "reporting_period" in result.columns
        # Should be sorted ascending
        assert result["reporting_period"].tolist() == ["12/31/2022", "3/31/2023"]

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_ubpr_series_calls_ubpr_endpoint(self, mock_create_adapter):
        """series='ubpr' should call retrieve_ubpr_reporting_periods."""
        mock_adapter = Mock()
        mock_adapter.retrieve_ubpr_reporting_periods.return_value = ["6/30/2023"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="ubpr",
            output_type="list",
            date_output_format="string_original",
        )

        mock_adapter.retrieve_ubpr_reporting_periods.assert_called_once()
        assert result == ["6/30/2023"]

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_date_output_format_string_original(self, mock_create_adapter):
        """string_original format should pass through dates unchanged."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = ["12/31/2023"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="call",
            output_type="list",
            date_output_format="string_original",
        )

        assert result == ["12/31/2023"]

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_date_output_format_other(self, mock_create_adapter):
        """Non-default date_output_format should still return data (format passthrough)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = ["12/31/2023"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="call",
            output_type="list",
            date_output_format="string_yyyymmdd",
        )

        # Current implementation passes through regardless of format
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_single_period_no_sort_needed(self, mock_create_adapter):
        """Single period should be returned as-is."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = ["12/31/2023"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="call",
            output_type="list",
        )

        assert result == ["12/31/2023"]


# ---------------------------------------------------------------------------
# collect_filers_on_reporting_period_enhanced
# ---------------------------------------------------------------------------
class TestCollectFilersOnReportingPeriodEnhanced:
    """Tests for collect_filers_on_reporting_period_enhanced."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_returns_normalized_list_with_dual_field_names(self, mock_create_adapter):
        """Pydantic-like filer objects should be normalized with both rssd and id_rssd."""
        # Use mock objects with model_dump to trigger the Pydantic normalization path
        mock_filer = Mock()
        mock_filer.model_dump.return_value = {
            "ID_RSSD": 480228,
            "FDICCertNumber": 12345,
            "OCCChartNumber": 0,
            "OTSDockNumber": 0,
            "PrimaryABARoutNumber": 0,
            "Name": "Test Bank",
            "State": "NY",
            "City": "New York",
            "Address": "123 Main St",
            "Zip": "10001",
            "FilingType": "041",
            "HasFiledForReportingPeriod": True,
        }

        mock_adapter = Mock()
        mock_adapter.retrieve_panel_of_reporters.return_value = [mock_filer]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_on_reporting_period_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            output_type="list",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        filer = result[0]
        # Both field names should exist after normalization
        assert "rssd" in filer
        assert "id_rssd" in filer
        assert filer["rssd"] == filer["id_rssd"]

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_pydantic_model_normalization(self, mock_create_adapter):
        """Pydantic-like objects with model_dump() should be normalized."""
        mock_filer = Mock()
        mock_filer.model_dump.return_value = {
            "ID_RSSD": 480228,
            "FDICCertNumber": 12345,
            "OCCChartNumber": 0,
            "OTSDockNumber": 0,
            "PrimaryABARoutNumber": 0,
            "Name": "Test Bank",
            "State": "NY",
            "City": "New York",
            "Address": "123 Main St",
            "Zip": "10001",
            "FilingType": "041",
            "HasFiledForReportingPeriod": True,
        }

        mock_adapter = Mock()
        mock_adapter.retrieve_panel_of_reporters.return_value = [mock_filer]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_on_reporting_period_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            output_type="list",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        filer = result[0]
        assert "rssd" in filer
        assert "id_rssd" in filer
        assert filer["rssd"] == "480228"
        assert filer["id_rssd"] == "480228"

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_returns_pandas_dataframe(self, mock_create_adapter):
        """output_type='pandas' should return a DataFrame."""
        mock_adapter = Mock()
        mock_adapter.retrieve_panel_of_reporters.return_value = [
            {
                "ID_RSSD": 480228,
                "FDICCertNumber": 0,
                "OCCChartNumber": 0,
                "OTSDockNumber": 0,
                "PrimaryABARoutNumber": 0,
                "Name": "Test Bank",
                "State": "NY",
                "City": "New York",
                "Address": "123 Main St",
                "Zip": "10001",
                "FilingType": "041",
                "HasFiledForReportingPeriod": True,
            }
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_on_reporting_period_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            output_type="pandas",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_datetime_reporting_period(self, mock_create_adapter):
        """Should accept a datetime object as reporting_period."""
        mock_adapter = Mock()
        mock_adapter.retrieve_panel_of_reporters.return_value = []
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_on_reporting_period_enhanced(
            session=None,
            creds=creds,
            reporting_period=datetime(2023, 12, 31),
            output_type="list",
        )

        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# collect_filers_since_date_enhanced
# ---------------------------------------------------------------------------
class TestCollectFilersSinceDateEnhanced:
    """Tests for collect_filers_since_date_enhanced."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_returns_string_rssd_ids(self, mock_create_adapter):
        """Returned RSSD IDs should be strings."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.return_value = ["480228", "12345"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_since_date_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            since_date="1/1/2023",
            output_type="list",
        )

        assert isinstance(result, list)
        assert result == ["480228", "12345"]
        # All should be strings
        assert all(isinstance(r, str) for r in result)

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_integer_rssd_ids_converted_to_strings(self, mock_create_adapter):
        """Integer RSSD IDs from adapter should be converted to strings."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.return_value = [480228, 12345]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_since_date_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            since_date="1/1/2023",
            output_type="list",
        )

        assert result == ["480228", "12345"]

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_pandas_output_has_dual_columns(self, mock_create_adapter):
        """Pandas output should have both rssd_id and rssd columns."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.return_value = ["480228"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_since_date_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            since_date="1/1/2023",
            output_type="pandas",
        )

        assert isinstance(result, pd.DataFrame)
        assert "rssd_id" in result.columns
        assert "rssd" in result.columns
        assert result["rssd_id"].tolist() == result["rssd"].tolist()

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_empty_list(self, mock_create_adapter):
        """Empty result from adapter should return empty list."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.return_value = []
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_since_date_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            since_date="1/1/2023",
            output_type="list",
        )

        assert result == []


# ---------------------------------------------------------------------------
# collect_filers_submission_date_time_enhanced
# ---------------------------------------------------------------------------
class TestCollectFilersSubmissionDateTimeEnhanced:
    """Tests for collect_filers_submission_date_time_enhanced."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_dict_submissions_dual_field_names(self, mock_create_adapter):
        """Dict submissions should produce both rssd and id_rssd fields."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2023 11:59:59 PM"},
            {"ID_RSSD": 12345, "DateTime": "12/31/2023 10:00:00 AM"},
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date="1/1/2023",
            reporting_period="12/31/2023",
            output_type="list",
            date_output_format="string_original",
        )

        assert isinstance(result, list)
        assert len(result) == 2
        for sub in result:
            assert "rssd" in sub
            assert "id_rssd" in sub
            assert sub["rssd"] == sub["id_rssd"]
            assert "datetime" in sub

        assert result[0]["rssd"] == "480228"
        assert result[1]["rssd"] == "12345"

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_pydantic_submissions_dual_field_names(self, mock_create_adapter):
        """Pydantic-like submission objects should be processed correctly."""
        mock_sub = Mock()
        mock_sub.ID_RSSD = 480228
        mock_sub.DateTime = "12/31/2023 11:59:59 PM"

        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [mock_sub]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date="1/1/2023",
            reporting_period="12/31/2023",
            output_type="list",
            date_output_format="string_original",
        )

        assert len(result) == 1
        assert result[0]["rssd"] == "480228"
        assert result[0]["id_rssd"] == "480228"
        assert result[0]["datetime"] == "12/31/2023 11:59:59 PM"

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_pandas_output(self, mock_create_adapter):
        """output_type='pandas' should return a DataFrame."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2023 11:59:59 PM"},
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date="1/1/2023",
            reporting_period="12/31/2023",
            output_type="pandas",
            date_output_format="string_original",
        )

        assert isinstance(result, pd.DataFrame)
        assert "rssd" in result.columns
        assert "id_rssd" in result.columns
        assert "datetime" in result.columns

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_date_output_format_yyyymmdd_converts(self, mock_create_adapter):
        """date_output_format='string_yyyymmdd' converts the datetime (rc6).

        Previously this parameter was a no-op stub; rc6 implemented the
        conversion. This test now asserts the new behavior.
        """
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2023 11:59:59 PM"},
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date="1/1/2023",
            reporting_period="12/31/2023",
            output_type="list",
            date_output_format="string_yyyymmdd",
        )

        # rc6: the datetime is parsed and reformatted; the time component is
        # dropped because YYYYMMDD is a date-only format.
        assert result[0]["datetime"] == "20231231"

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_date_output_format_string_original_passthrough(self, mock_create_adapter):
        """date_output_format='string_original' (default) passes through unchanged."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2023 11:59:59 PM"},
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date="1/1/2023",
            reporting_period="12/31/2023",
            output_type="list",
            date_output_format="string_original",
        )

        assert result[0]["datetime"] == "12/31/2023 11:59:59 PM"


# ---------------------------------------------------------------------------
# _normalize_pydantic_to_soap_format
# ---------------------------------------------------------------------------
class TestNormalizePydanticToSoapFormat:
    """Tests for _normalize_pydantic_to_soap_format helper."""

    def test_with_pydantic_model_having_model_dump(self):
        """Pydantic models (with model_dump) should be normalized via datahelpers."""
        mock_model = Mock()
        mock_model.model_dump.return_value = {
            "ID_RSSD": 480228,
            "FDICCertNumber": 12345,
            "OCCChartNumber": 0,
            "OTSDockNumber": 0,
            "PrimaryABARoutNumber": 0,
            "Name": "Test Bank",
            "State": "NY",
            "City": "New York",
            "Address": "123 Main St",
            "Zip": "10001",
            "FilingType": "041",
            "HasFiledForReportingPeriod": True,
        }

        result = _normalize_pydantic_to_soap_format(mock_model)

        mock_model.model_dump.assert_called_once()
        assert isinstance(result, dict)
        assert "rssd" in result
        assert "id_rssd" in result
        assert result["rssd"] == "480228"
        assert result["id_rssd"] == "480228"

    def test_with_plain_dict(self):
        """Plain dicts without model_dump should be normalized directly."""
        input_dict = {
            "ID_RSSD": 480228,
            "FDICCertNumber": 0,
            "OCCChartNumber": 0,
            "OTSDockNumber": 0,
            "PrimaryABARoutNumber": 0,
            "Name": "Test Bank",
            "State": "NY",
            "City": "New York",
            "Address": "123 Main St",
            "Zip": "10001",
            "FilingType": "041",
            "HasFiledForReportingPeriod": True,
        }

        result = _normalize_pydantic_to_soap_format(input_dict)

        assert isinstance(result, dict)
        assert "rssd" in result
        assert "id_rssd" in result
        assert result["rssd"] == "480228"

    def test_missing_rssd_returns_none(self):
        """Dict without ID_RSSD should set rssd/id_rssd to None."""
        input_dict = {
            "Name": "Test Bank",
            "State": "NY",
            "City": "New York",
        }

        result = _normalize_pydantic_to_soap_format(input_dict)

        assert result.get("rssd") is None
        assert result.get("id_rssd") is None


# ---------------------------------------------------------------------------
# _format_datetime_for_output
# ---------------------------------------------------------------------------
class TestFormatDatetimeForOutput:
    """Tests for _format_datetime_for_output helper."""

    def test_string_original_returns_as_is(self):
        """string_original format should return the datetime string unchanged."""
        dt_str = "12/31/2023 11:59:59 PM"
        result = _format_datetime_for_output(dt_str, "string_original")
        assert result == dt_str

    def test_other_format_returns_as_is(self):
        """Non-string_original formats also pass through (current implementation)."""
        dt_str = "12/31/2023 11:59:59 PM"
        result = _format_datetime_for_output(dt_str, "string_YYYYMMDD")
        assert result == dt_str

    def test_empty_string_returns_empty(self):
        """Empty string should be returned as-is (falsy check)."""
        result = _format_datetime_for_output("", "string_original")
        assert result == ""

    def test_none_returns_none(self):
        """None should be returned as-is (falsy check)."""
        result = _format_datetime_for_output(None, "string_original")
        assert result is None


# ---------------------------------------------------------------------------
# Additional coverage tests for methods_enhanced.py
# ---------------------------------------------------------------------------


class TestCollectReportingPeriodsEnhancedExtended:
    """Additional tests for collect_reporting_periods_enhanced coverage."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_invalid_series_hits_validation_branch(self, mock_create_adapter):
        """Invalid series should trigger the validation branch (line 123).

        The ValidationError is raised at line 123 but caught by the broad
        except at line 170, which then re-raises via raise_exception.
        """
        mock_adapter = Mock()
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        with pytest.raises(Exception):
            collect_reporting_periods_enhanced(
                session=None,
                creds=creds,
                series="invalid_series",
                output_type="list",
                date_output_format="string_original",
            )

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_exception_from_adapter_hits_error_handler(self, mock_create_adapter):
        """Exception from adapter should reach the except block (lines 170-172)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.side_effect = Exception("API down")
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        with pytest.raises(Exception):
            collect_reporting_periods_enhanced(
                session=None,
                creds=creds,
                series="call",
                output_type="list",
                date_output_format="string_original",
            )


class TestCollectReportingPeriodsEnhancedPolars:
    """Test polars output for collect_reporting_periods_enhanced (line 166)."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_polars_output_type(self, mock_create_adapter):
        """output_type='polars' should return a polars DataFrame (line 166)."""
        import polars as pl_mod

        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = [
            "12/31/2023",
            "6/30/2023",
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_reporting_periods_enhanced(
            session=None,
            creds=creds,
            series="call",
            output_type="polars",
            date_output_format="string_original",
        )

        assert isinstance(result, pl_mod.DataFrame)
        assert "reporting_period" in result.columns


class TestCollectFilersOnReportingPeriodEnhancedValidation:
    """Tests for validation paths in collect_filers_on_reporting_period_enhanced."""

    def test_invalid_reporting_period_raises_validation_error(self):
        """Invalid reporting_period should raise ValidationError (line 208)."""
        creds = _make_creds()
        with pytest.raises(ValidationError, match="reporting_period"):
            collect_filers_on_reporting_period_enhanced(
                session=None,
                creds=creds,
                reporting_period="not-a-date",
                output_type="list",
            )

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    @patch(
        "ffiec_data_connect.methods_enhanced._convert_any_date_to_ffiec_format",
        return_value=None,
    )
    def test_unconvertible_period_raises_validation_error(
        self, mock_convert, mock_create_adapter
    ):
        """Period that passes validation but fails conversion should raise (line 223)."""
        creds = _make_creds()
        with pytest.raises(ValidationError, match="reporting_period"):
            collect_filers_on_reporting_period_enhanced(
                session=None,
                creds=creds,
                reporting_period="12/31/2023",  # passes _is_valid but mock says can't convert
                output_type="list",
            )


class TestCollectFilersOnReportingPeriodEnhancedExtended:
    """Additional tests for collect_filers_on_reporting_period_enhanced coverage."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_polars_output_type(self, mock_create_adapter):
        """output_type='polars' should return a polars DataFrame (lines 248-249)."""
        import polars as pl_mod

        mock_adapter = Mock()
        mock_adapter.retrieve_panel_of_reporters.return_value = [
            {
                "ID_RSSD": 480228,
                "FDICCertNumber": 0,
                "OCCChartNumber": 0,
                "OTSDockNumber": 0,
                "PrimaryABARoutNumber": 0,
                "Name": "Test Bank",
                "State": "NY",
                "City": "New York",
                "Address": "123 Main St",
                "Zip": "10001",
                "FilingType": "041",
                "HasFiledForReportingPeriod": True,
            }
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_on_reporting_period_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            output_type="polars",
        )

        assert isinstance(result, pl_mod.DataFrame)
        assert len(result) == 1


class TestCollectFilersSinceDateEnhancedExtended:
    """Additional tests for collect_filers_since_date_enhanced coverage."""

    def test_invalid_reporting_period_raises_validation_error(self):
        """Invalid reporting_period should raise ValidationError (line 208)."""
        creds = _make_creds()
        with pytest.raises(ValidationError, match="reporting_period"):
            collect_filers_since_date_enhanced(
                session=None,
                creds=creds,
                reporting_period="not-a-date",
                since_date="1/1/2023",
                output_type="list",
            )

    def test_invalid_since_date_raises_validation_error(self):
        """Invalid since_date should raise ValidationError (line 223)."""
        creds = _make_creds()
        with pytest.raises(ValidationError, match="since_date"):
            collect_filers_since_date_enhanced(
                session=None,
                creds=creds,
                reporting_period="12/31/2023",
                since_date="not-a-date",
                output_type="list",
            )

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_polars_output_type(self, mock_create_adapter):
        """output_type='polars' should return a polars DataFrame (lines 250, 254-258)."""
        import polars as pl_mod

        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.return_value = ["480228", "12345"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_since_date_enhanced(
            session=None,
            creds=creds,
            reporting_period="12/31/2023",
            since_date="1/1/2023",
            output_type="polars",
        )

        assert isinstance(result, pl_mod.DataFrame)
        assert "rssd_id" in result.columns
        assert "rssd" in result.columns


class TestCollectFilersSubmissionDateTimeEnhancedExtended:
    """Additional tests for collect_filers_submission_date_time_enhanced coverage."""

    def test_invalid_reporting_period_raises_validation_error(self):
        """Invalid reporting_period should raise ValidationError (lines 289, 394)."""
        creds = _make_creds()
        with pytest.raises(ValidationError, match="reporting_period"):
            collect_filers_submission_date_time_enhanced(
                session=None,
                creds=creds,
                since_date="1/1/2023",
                reporting_period="not-valid",
                output_type="list",
                date_output_format="string_original",
            )

    def test_invalid_since_date_raises_validation_error(self):
        """Invalid since_date should raise ValidationError (lines 299, 403)."""
        creds = _make_creds()
        with pytest.raises(ValidationError, match="since_date"):
            collect_filers_submission_date_time_enhanced(
                session=None,
                creds=creds,
                since_date="not-valid",
                reporting_period="12/31/2023",
                output_type="list",
                date_output_format="string_original",
            )

    def test_datetime_inputs_converted(self):
        """datetime objects should be converted via _create_ffiec_date_from_datetime (lines 311, 415)."""
        creds = _make_creds()
        # Pass datetime objects that will fail conversion (non-quarter-end)
        # to trigger the "could not convert" validation error
        with pytest.raises((ValidationError, ConnectionError)):
            collect_filers_submission_date_time_enhanced(
                session=None,
                creds=creds,
                since_date=datetime(2023, 2, 15),  # not a quarter end
                reporting_period=datetime(2023, 2, 15),  # not a quarter end
                output_type="list",
                date_output_format="string_original",
            )

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_polars_output_type(self, mock_create_adapter):
        """output_type='polars' should return a polars DataFrame (lines 351-352, 356-358)."""
        import polars as pl_mod

        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2023 11:59:59 PM"},
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date="1/1/2023",
            reporting_period="12/31/2023",
            output_type="polars",
            date_output_format="string_original",
        )

        assert isinstance(result, pl_mod.DataFrame)
        assert "rssd" in result.columns
        assert "id_rssd" in result.columns
        assert "datetime" in result.columns

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_exception_from_adapter_hits_error_handler(self, mock_create_adapter):
        """Exception from adapter should reach the except block (lines 474-481)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.side_effect = Exception(
            "API failure"
        )
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        with pytest.raises(Exception):
            collect_filers_submission_date_time_enhanced(
                session=None,
                creds=creds,
                since_date="1/1/2023",
                reporting_period="12/31/2023",
                output_type="list",
                date_output_format="string_original",
            )


# ---------------------------------------------------------------------------
# New tests for 100% coverage
# ---------------------------------------------------------------------------


class TestPolarsImportFallbackEnhanced:
    """Test polars import fallback path (lines 37-39)."""

    def test_polars_import_failure_sets_flag_false(self):
        """When polars import fails, POLARS_AVAILABLE should be False and pl None."""
        import importlib
        import sys

        original_polars = sys.modules.get("polars")

        try:
            sys.modules["polars"] = None  # type: ignore[assignment]

            import ffiec_data_connect.methods_enhanced as me_mod

            importlib.reload(me_mod)

            assert me_mod.POLARS_AVAILABLE is False
            assert me_mod.pl is None
        finally:
            if original_polars is not None:
                sys.modules["polars"] = original_polars
            else:
                sys.modules.pop("polars", None)
            importlib.reload(me_mod)


class TestSchemaValidationWarning:
    """Test that schema validation warnings are logged (line 146)."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    @patch("ffiec_data_connect.methods_enhanced.DataNormalizer")
    def test_incompatible_schema_logs_warning(
        self, mock_normalizer_cls, mock_create_adapter
    ):
        """When validate_pydantic_compatibility returns compatible=False, logger.warning fires (line 146)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_reporting_periods.return_value = ["12/31/2023"]
        mock_create_adapter.return_value = mock_adapter

        mock_normalizer_cls.validate_pydantic_compatibility.return_value = {
            "compatible": False,
            "warnings": ["Item 0 missing ID_RSSD"],
            "recommendations": [],
            "endpoint": "RetrieveReportingPeriods",
        }

        creds = _make_creds()

        with patch("ffiec_data_connect.methods_enhanced.logger") as mock_logger:
            result = collect_reporting_periods_enhanced(
                session=None,
                creds=creds,
                series="call",
                output_type="list",
                date_output_format="string_original",
            )
            # Verify the warning was logged
            mock_logger.warning.assert_called_once()
            assert "Schema validation warnings" in mock_logger.warning.call_args[0][0]

        assert isinstance(result, list)


class TestCollectFilersOnReportingPeriodEnhancedExceptBlock:
    """Cover the except block in collect_filers_on_reporting_period_enhanced (lines 253-257)."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_adapter_exception_hits_except_block(self, mock_create_adapter):
        """Exception from adapter triggers the except block (lines 253-257)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_panel_of_reporters.side_effect = RuntimeError("API down")
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        with pytest.raises((ConnectionError, Exception)):
            collect_filers_on_reporting_period_enhanced(
                session=None,
                creds=creds,
                reporting_period="12/31/2023",
                output_type="list",
            )


class TestCollectFilersSinceDateEnhancedDatetimeInputs:
    """Cover datetime conversion in collect_filers_since_date_enhanced (lines 310, 315, 320)."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_datetime_reporting_period_and_since_date(self, mock_create_adapter):
        """datetime objects for both reporting_period and since_date (lines 310, 315)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.return_value = ["480228"]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_since_date_enhanced(
            session=None,
            creds=creds,
            reporting_period=datetime(2023, 12, 31),
            since_date=datetime(2023, 6, 30),
            output_type="list",
        )
        assert isinstance(result, list)
        assert result == ["480228"]

    @patch("ffiec_data_connect.methods_enhanced._convert_any_date_to_ffiec_format")
    def test_none_date_conversion_raises_validation_error(self, mock_convert):
        """When date conversion returns None, ValidationError is raised (line 320)."""
        mock_convert.return_value = None

        creds = _make_creds()
        with pytest.raises((ValidationError, Exception)):
            collect_filers_since_date_enhanced(
                session=None,
                creds=creds,
                reporting_period="12/31/2023",
                since_date="1/1/2023",
                output_type="list",
            )


class TestCollectFilersSinceDateEnhancedExceptBlock:
    """Cover the except block in collect_filers_since_date_enhanced (lines 353-355)."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_adapter_exception_hits_except_block(self, mock_create_adapter):
        """Exception from adapter triggers the except block (lines 353-355)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_since_date.side_effect = RuntimeError("API down")
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        with pytest.raises((ConnectionError, Exception)):
            collect_filers_since_date_enhanced(
                session=None,
                creds=creds,
                reporting_period="12/31/2023",
                since_date="1/1/2023",
                output_type="list",
            )


class TestCollectFilersSubmissionDateTimeEnhancedDatetimeInputs:
    """Cover datetime conversion in collect_filers_submission_date_time_enhanced (lines 412, 417, 422)."""

    @patch("ffiec_data_connect.methods_enhanced.create_protocol_adapter")
    def test_datetime_reporting_period_and_since_date_happy_path(
        self, mock_create_adapter
    ):
        """datetime objects for both reporting_period and since_date succeed (lines 412, 417)."""
        mock_adapter = Mock()
        mock_adapter.retrieve_filers_submission_datetime.return_value = [
            {"ID_RSSD": 480228, "DateTime": "12/31/2023 11:59:59 PM"},
        ]
        mock_create_adapter.return_value = mock_adapter

        creds = _make_creds()
        result = collect_filers_submission_date_time_enhanced(
            session=None,
            creds=creds,
            since_date=datetime(2023, 6, 30),
            reporting_period=datetime(2023, 12, 31),
            output_type="list",
            date_output_format="string_original",
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["rssd"] == "480228"

    @patch("ffiec_data_connect.methods_enhanced._convert_any_date_to_ffiec_format")
    def test_none_date_conversion_raises_validation_error(self, mock_convert):
        """When date conversion returns None, ValidationError is raised (line 422)."""
        mock_convert.return_value = None

        creds = _make_creds()
        with pytest.raises((ValidationError, Exception)):
            collect_filers_submission_date_time_enhanced(
                session=None,
                creds=creds,
                since_date="1/1/2023",
                reporting_period="12/31/2023",
                output_type="list",
                date_output_format="string_original",
            )
