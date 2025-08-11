"""
Comprehensive unit tests for methods.py with memory leak focus.

Tests FFIEC webservice method wrappers, validation, data processing, and memory management.
"""

import gc
import tracemalloc
from datetime import datetime, timezone
from typing import Any, Dict, List, Union
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest
import requests

from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.exceptions import ConnectionError, NoDataError, ValidationError
from ffiec_data_connect.ffiec_connection import FFIECConnection
from ffiec_data_connect.methods import (
    _client_factory,
    _convert_any_date_to_ffiec_format,
    _convert_quarter_to_date,
    _create_ffiec_date_from_datetime,
    _credentials_validator,
    _date_format_validator,
    _is_valid_date_or_quarter,
    _output_type_validator,
    _return_client_session,
    _return_ffiec_reporting_date,
    _session_validator,
    _validate_rssd_id,
    collect_data,
    collect_filers_on_reporting_period,
    collect_filers_since_date,
    collect_filers_submission_date_time,
    collect_reporting_periods,
)


class TestDateUtilities:
    """Test date conversion and validation utilities."""

    def test_create_ffiec_date_from_datetime(self):
        """Test FFIEC date creation from datetime object."""
        # Test typical dates
        test_date = datetime(2023, 12, 31)
        result = _create_ffiec_date_from_datetime(test_date)
        assert result == "12/31/2023"

        # Test edge cases
        test_date = datetime(2023, 3, 31)
        result = _create_ffiec_date_from_datetime(test_date)
        assert result == "3/31/2023"

        test_date = datetime(2023, 1, 1)
        result = _create_ffiec_date_from_datetime(test_date)
        assert result == "1/1/2023"

    def test_convert_any_date_to_ffiec_format(self):
        """Test conversion of various date formats to FFIEC format."""
        # Test datetime object
        test_date = datetime(2023, 12, 31)
        result = _convert_any_date_to_ffiec_format(test_date)
        assert result == "12/31/2023"

        # Test YYYY-MM-DD format
        result = _convert_any_date_to_ffiec_format("2023-12-31")
        assert result == "12/31/2023"

        # Test MM/DD/YYYY format (should pass through)
        result = _convert_any_date_to_ffiec_format("12/31/2023")
        assert result == "12/31/2023"

        # Test YYYYMMDD format
        result = _convert_any_date_to_ffiec_format("20231231")
        assert result == "12/31/2023"

    def test_convert_any_date_invalid_format(self):
        """Test error handling for invalid date formats."""
        # The function returns None for invalid string formats, not raise error
        result = _convert_any_date_to_ffiec_format("invalid-date")
        assert result is None

        # But it does raise an error for invalid types
        with pytest.raises(ValueError):
            _convert_any_date_to_ffiec_format(123)

    def test_convert_quarter_to_date(self):
        """Test quarter string conversion to datetime."""
        # Test all quarters
        result = _convert_quarter_to_date("1Q2023")
        assert result == datetime(2023, 3, 31)

        result = _convert_quarter_to_date("2Q2023")
        assert result == datetime(2023, 6, 30)

        result = _convert_quarter_to_date("3Q2023")
        assert result == datetime(2023, 9, 30)

        result = _convert_quarter_to_date("4Q2023")
        assert result == datetime(2023, 12, 31)

        # Test lowercase q
        result = _convert_quarter_to_date("1q2023")
        assert result == datetime(2023, 3, 31)

    def test_is_valid_date_or_quarter(self):
        """Test date and quarter validation."""
        # Test valid datetime objects (quarter ends)
        assert _is_valid_date_or_quarter(datetime(2023, 3, 31)) is True
        assert _is_valid_date_or_quarter(datetime(2023, 6, 30)) is True
        assert _is_valid_date_or_quarter(datetime(2023, 9, 30)) is True
        assert _is_valid_date_or_quarter(datetime(2023, 12, 31)) is True

        # Test invalid datetime objects (not quarter ends)
        assert _is_valid_date_or_quarter(datetime(2023, 3, 30)) is False
        assert _is_valid_date_or_quarter(datetime(2023, 6, 29)) is False
        # Month 4 (April) is not a quarter-end month, so function returns None (implicitly False)
        result = _is_valid_date_or_quarter(datetime(2023, 4, 30))
        assert result is None or result is False

        # Test valid string formats
        assert _is_valid_date_or_quarter("1Q2023") is True
        assert _is_valid_date_or_quarter("2023-12-31") is True
        assert _is_valid_date_or_quarter("20231231") is True
        assert _is_valid_date_or_quarter("12/31/2023") is True

        # Test invalid strings
        assert _is_valid_date_or_quarter("invalid") is False
        assert _is_valid_date_or_quarter("5Q2023") is False

        # Test invalid types
        assert _is_valid_date_or_quarter(123) is False
        assert _is_valid_date_or_quarter(None) is False

    def test_return_ffiec_reporting_date(self):
        """Test FFIEC reporting date generation."""
        # Test datetime input
        test_date = datetime(2023, 12, 31)
        result = _return_ffiec_reporting_date(test_date)
        assert result == "12/31/2023"

        # Test quarter string input
        result = _return_ffiec_reporting_date("1Q2023")
        assert result == "3/31/2023"

        # Test regular date string
        result = _return_ffiec_reporting_date("2023-12-31")
        assert result == "12/31/2023"

    def test_return_ffiec_reporting_date_invalid(self):
        """Test error handling for invalid reporting dates."""
        # Test invalid date (not quarter end)
        with pytest.raises(ValueError):
            _return_ffiec_reporting_date("2023-04-15")


class TestValidators:
    """Test input validation functions."""

    def test_output_type_validator(self):
        """Test output type validation."""
        # Valid types
        assert _output_type_validator("list") is True
        assert _output_type_validator("pandas") is True

        # Invalid types
        with pytest.raises((ValidationError, ValueError)):
            _output_type_validator("invalid")

        with pytest.raises((ValidationError, ValueError)):
            _output_type_validator("dict")

    def test_date_format_validator(self):
        """Test date format validation."""
        # Valid formats
        assert _date_format_validator("string_original") is True
        assert _date_format_validator("string_yyyymmdd") is True
        assert _date_format_validator("python_format") is True

        # Invalid formats
        with pytest.raises((ValidationError, ValueError)):
            _date_format_validator("invalid")

        with pytest.raises((ValidationError, ValueError)):
            _date_format_validator("datetime")

    def test_credentials_validator(self):
        """Test credentials validation."""
        # Valid credentials
        creds = Mock(spec=WebserviceCredentials)
        assert _credentials_validator(creds) is True

        # Invalid credentials
        with pytest.raises((ValidationError, ValueError)):
            _credentials_validator("invalid")

        with pytest.raises((ValidationError, ValueError)):
            _credentials_validator(None)

    def test_session_validator(self):
        """Test session validation."""
        # Valid sessions
        session = Mock(spec=FFIECConnection)
        assert _session_validator(session) is True

        session = Mock(spec=requests.Session)
        assert _session_validator(session) is True

        # Invalid sessions
        with pytest.raises((ValidationError, ValueError)):
            _session_validator("invalid")

        with pytest.raises((ValidationError, ValueError)):
            _session_validator(None)

    def test_validate_rssd_id(self):
        """Test RSSD ID validation and conversion."""
        # Valid RSSD IDs
        assert _validate_rssd_id("123456") == 123456
        assert _validate_rssd_id("12345678") == 12345678
        assert _validate_rssd_id("  123456  ") == 123456  # Whitespace trimmed

        # Invalid RSSD IDs
        with pytest.raises((ValidationError, ValueError)):
            _validate_rssd_id("")

        with pytest.raises((ValidationError, ValueError)):
            _validate_rssd_id("abc123")

        with pytest.raises((ValidationError, ValueError)):
            _validate_rssd_id("0")  # Zero not allowed

        with pytest.raises((ValidationError, ValueError)):
            _validate_rssd_id("123456789")  # Too long

        with pytest.raises((ValidationError, ValueError)):
            _validate_rssd_id("-123")  # Negative

    def test_validate_rssd_id_memory_efficiency(self):
        """Test RSSD ID validation doesn't leak memory on large inputs."""
        tracemalloc.start()

        # Test many validations
        for i in range(1000):
            try:
                _validate_rssd_id(f"{i:08d}")
            except:
                pass

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not consume excessive memory (less than 1MB for 1000 operations)
        assert peak < 1024 * 1024


class TestClientManagement:
    """Test client creation and caching."""

    @patch("ffiec_data_connect.soap_cache.get_soap_client")
    def test_return_client_session(self, mock_get_soap_client):
        """Test client session creation with caching."""
        mock_client = Mock()
        mock_get_soap_client.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = _return_client_session(session, creds)

        assert result is mock_client
        mock_get_soap_client.assert_called_once_with(creds, session)

    def test_client_factory_ffiec_connection(self):
        """Test client factory with FFIECConnection."""
        with patch(
            "ffiec_data_connect.methods._return_client_session"
        ) as mock_return_client:
            mock_client = Mock()
            mock_return_client.return_value = mock_client

            session = Mock(spec=FFIECConnection)
            session.session = Mock(spec=requests.Session)
            creds = Mock()

            result = _client_factory(session, creds)

            assert result is mock_client
            mock_return_client.assert_called_once_with(session.session, creds)

    def test_client_factory_requests_session(self):
        """Test client factory with requests.Session."""
        with patch(
            "ffiec_data_connect.methods._return_client_session"
        ) as mock_return_client:
            mock_client = Mock()
            mock_return_client.return_value = mock_client

            import requests

            session = Mock(spec=requests.Session)
            creds = Mock()

            result = _client_factory(session, creds)

            assert result is mock_client
            mock_return_client.assert_called_once_with(session, creds)

    def test_client_factory_invalid_session(self):
        """Test client factory with invalid session type."""
        with pytest.raises(Exception) as exc_info:
            _client_factory("invalid", Mock())

        assert "Invalid session" in str(exc_info.value)


class TestCollectReportingPeriods:
    """Test collect_reporting_periods function."""

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_reporting_periods_call_series(self, mock_client_factory):
        """Test collecting reporting periods for call series."""
        # Mock client and response
        mock_client = Mock()
        mock_client.service.RetrieveReportingPeriods.return_value = [
            "2023-12-31",
            "2023-09-30",
            "2023-06-30",
        ]
        mock_client_factory.return_value = mock_client

        # Create mock session and credentials
        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_reporting_periods(session, creds, series="call")

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 3
        assert "2023-12-31" in result

        # Verify client was called correctly
        mock_client.service.RetrieveReportingPeriods.assert_called_once_with(
            dataSeries="Call"
        )

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_reporting_periods_ubpr_series(self, mock_client_factory):
        """Test collecting reporting periods for UBPR series."""
        mock_client = Mock()
        mock_client.service.RetrieveUBPRReportingPeriods.return_value = [
            "2023-12-31",
            "2023-09-30",
        ]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_reporting_periods(session, creds, series="ubpr")

        assert isinstance(result, list)
        assert len(result) == 2
        mock_client.service.RetrieveUBPRReportingPeriods.assert_called_once()

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_reporting_periods_pandas_output(self, mock_client_factory):
        """Test pandas DataFrame output."""
        mock_client = Mock()
        mock_client.service.RetrieveReportingPeriods.return_value = [
            "2023-12-31",
            "2023-09-30",
        ]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_reporting_periods(session, creds, output_type="pandas")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "reporting_period" in result.columns

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_reporting_periods_date_formatting(self, mock_client_factory):
        """Test different date output formats."""
        mock_client = Mock()
        mock_client.service.RetrieveReportingPeriods.return_value = ["2023-12-31"]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        # Test yyyymmdd format
        result = collect_reporting_periods(
            session, creds, date_output_format="string_yyyymmdd"
        )
        assert result[0] == "20231231"

        # Test python format
        result = collect_reporting_periods(
            session, creds, date_output_format="python_format"
        )
        assert isinstance(result[0], datetime)
        assert result[0].year == 2023
        assert result[0].month == 12
        assert result[0].day == 31

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_reporting_periods_no_data(self, mock_client_factory):
        """Test handling when no reporting periods are available."""
        mock_client = Mock()
        mock_client.service.RetrieveReportingPeriods.return_value = []
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        with pytest.raises((NoDataError, ValueError)):
            collect_reporting_periods(session, creds)

    def test_collect_reporting_periods_validation(self):
        """Test input validation for collect_reporting_periods."""
        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        # Test invalid output_type
        with pytest.raises((ValidationError, ValueError)):
            collect_reporting_periods(session, creds, output_type="invalid")

        # Test invalid date_output_format
        with pytest.raises((ValidationError, ValueError)):
            collect_reporting_periods(session, creds, date_output_format="invalid")


class TestCollectData:
    """Test collect_data function."""

    @patch("ffiec_data_connect.xbrl_processor._process_xml")
    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_data_call_series(self, mock_client_factory, mock_process_xml):
        """Test collecting data for call series."""
        # Mock XBRL response
        mock_xml_data = b"<mock_xbrl_data/>"

        # Mock processed data
        mock_processed_data = [
            {
                "mdrm": "RCON0010",
                "rssd": "123456",
                "quarter": "2023-12-31",
                "data_type": "int",
                "int_data": 1000000,
                "float_data": None,
                "bool_data": None,
                "str_data": None,
            }
        ]

        # Setup mocks
        mock_client = Mock()
        mock_client.service.RetrieveFacsimile.return_value = mock_xml_data
        mock_client_factory.return_value = mock_client
        mock_process_xml.return_value = mock_processed_data

        # Test the function
        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_data(
            session=session,
            creds=creds,
            reporting_period="2023-12-31",
            rssd_id="123456",
            series="call",
        )

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["mdrm"] == "RCON0010"
        assert result[0]["int_data"] == 1000000

        # Verify service was called correctly
        mock_client.service.RetrieveFacsimile.assert_called_once_with(
            dataSeries="Call",
            fiIDType="ID_RSSD",
            fiID=123456,
            reportingPeriodEndDate="12/31/2023",
            facsimileFormat="XBRL",
        )

        # Verify XML processing
        mock_process_xml.assert_called_once_with(mock_xml_data, "string_original")

    @patch("ffiec_data_connect.xbrl_processor._process_xml")
    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_data_ubpr_series(self, mock_client_factory, mock_process_xml):
        """Test collecting data for UBPR series."""
        mock_xml_data = b"<mock_ubpr_data/>"
        mock_processed_data = [{"test": "data"}]

        mock_client = Mock()
        mock_client.service.RetrieveUBPRXBRLFacsimile.return_value = mock_xml_data
        mock_client_factory.return_value = mock_client
        mock_process_xml.return_value = mock_processed_data

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_data(
            session=session,
            creds=creds,
            reporting_period="1Q2023",
            rssd_id="123456",
            series="ubpr",
        )

        assert isinstance(result, list)
        mock_client.service.RetrieveUBPRXBRLFacsimile.assert_called_once_with(
            fiIDType="ID_RSSD", fiID=123456, reportingPeriodEndDate="3/31/2023"
        )

    @patch("ffiec_data_connect.xbrl_processor._process_xml")
    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_data_pandas_output(self, mock_client_factory, mock_process_xml):
        """Test pandas DataFrame output."""
        mock_processed_data = [{"test": "data"}, {"test2": "data2"}]

        mock_client = Mock()
        mock_client.service.RetrieveFacsimile.return_value = b"<mock/>"
        mock_client_factory.return_value = mock_client
        mock_process_xml.return_value = mock_processed_data

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_data(
            session=session,
            creds=creds,
            reporting_period="2023-12-31",
            rssd_id="123456",
            series="call",
            output_type="pandas",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_data_validation(self, mock_client_factory):
        """Test input validation for collect_data."""
        # Mock the client factory to avoid credential encoding issues
        mock_client = Mock()
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        # Test invalid RSSD ID - should fail at RSSD validation step
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            collect_data(session, creds, "2023-12-31", "invalid", "call")

        # Verify it's the RSSD validation that failed
        error_message = str(exc_info.value)
        assert "rssd" in error_message.lower() or "numeric" in error_message.lower()

        # Test invalid output type - should fail at output type validation
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            collect_data(
                session, creds, "2023-12-31", "123456", "call", output_type="invalid"
            )

        # Verify it's output type validation that failed
        error_message = str(exc_info.value)
        assert (
            "output_type" in error_message.lower() or "invalid" in error_message.lower()
        )


class TestMemoryLeakPrevention:
    """Test memory leak prevention in methods."""

    @patch("ffiec_data_connect.methods._client_factory")
    def test_reporting_periods_memory_usage(self, mock_client_factory):
        """Test that collect_reporting_periods doesn't leak memory."""
        # Setup large mock data
        large_periods_list = [f"2023-{i:02d}-31" for i in range(1, 13)] * 100

        mock_client = Mock()
        mock_client.service.RetrieveReportingPeriods.return_value = large_periods_list
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        # Track memory usage
        tracemalloc.start()

        # Run multiple times to detect leaks
        for _ in range(10):
            result = collect_reporting_periods(session, creds)
            # Force cleanup
            del result
            gc.collect()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not consume excessive memory
        # Allow up to 10MB for large dataset processing
        assert peak < 10 * 1024 * 1024

    @patch("ffiec_data_connect.xbrl_processor._process_xml")
    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_data_memory_usage(self, mock_client_factory, mock_process_xml):
        """Test that collect_data doesn't leak memory with large datasets."""
        # Create large mock processed data
        large_dataset = []
        for i in range(1000):
            large_dataset.append(
                {
                    "mdrm": f"RCON{i:04d}",
                    "rssd": "123456",
                    "quarter": "2023-12-31",
                    "data_type": "int",
                    "int_data": i * 1000,
                    "float_data": None,
                    "bool_data": None,
                    "str_data": None,
                }
            )

        mock_client = Mock()
        mock_client.service.RetrieveFacsimile.return_value = b"<large_mock_data/>"
        mock_client_factory.return_value = mock_client
        mock_process_xml.return_value = large_dataset

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        # Track memory usage
        tracemalloc.start()

        # Run multiple times
        for _ in range(5):
            result = collect_data(session, creds, "2023-12-31", "123456", "call")
            # Process data to simulate real usage
            if isinstance(result, list):
                sum([row.get("int_data", 0) for row in result if row.get("int_data")])
            del result
            gc.collect()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not consume excessive memory for repeated operations
        assert peak < 50 * 1024 * 1024  # 50MB limit

    def test_date_conversion_memory_efficiency(self):
        """Test that date conversion functions don't leak memory."""
        tracemalloc.start()

        # Test many date conversions
        for i in range(10000):
            test_date = datetime(2023, 12, 31)
            result = _create_ffiec_date_from_datetime(test_date)

            # Test various formats
            try:
                _convert_any_date_to_ffiec_format("2023-12-31")
                _convert_any_date_to_ffiec_format("20231231")
                _convert_any_date_to_ffiec_format("12/31/2023")
            except:
                pass

            if i % 1000 == 0:
                gc.collect()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should be very memory efficient for simple string operations
        assert peak < 5 * 1024 * 1024  # 5MB limit


class TestCollectFilersSinceDate:
    """Test collect_filers_since_date function."""

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_filers_since_date(self, mock_client_factory):
        """Test basic functionality of collect_filers_since_date."""
        mock_client = Mock()
        mock_client.service.RetrieveFilersSinceDate.return_value = [
            "123456",
            "789012",
            "345678",
        ]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_filers_since_date(
            session=session,
            creds=creds,
            reporting_period="2023-12-31",
            since_date="2023-12-01",
        )

        assert isinstance(result, list)
        assert len(result) == 3
        assert "123456" in result

        mock_client.service.RetrieveFilersSinceDate.assert_called_once_with(
            dataSeries="Call",
            lastUpdateDateTime="12/1/2023",
            reportingPeriodEndDate="12/31/2023",
        )

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_filers_since_date_pandas_output(self, mock_client_factory):
        """Test pandas output for collect_filers_since_date."""
        mock_client = Mock()
        mock_client.service.RetrieveFilersSinceDate.return_value = ["123456", "789012"]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_filers_since_date(
            session=session,
            creds=creds,
            reporting_period="1Q2023",
            since_date="2023-03-01",
            output_type="pandas",
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "rssd_id" in result.columns

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_filers_since_date_validation(self, mock_client_factory):
        """Test validation for collect_filers_since_date."""
        # Mock client factory to avoid credential issues
        mock_client = Mock()
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        # Test invalid reporting period - mock the validation to avoid client creation
        with patch(
            "ffiec_data_connect.methods._is_valid_date_or_quarter"
        ) as mock_valid:
            mock_valid.return_value = False

            with pytest.raises(ValueError) as exc_info:
                collect_filers_since_date(
                    session, creds, "2023-04-15", "2023-03-01"  # Not quarter end
                )

            error_message = str(exc_info.value)
            assert "reporting period" in error_message.lower()


class TestCollectFilersSubmissionDateTime:
    """Test collect_filers_submission_date_time function."""

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_filers_submission_date_time(self, mock_client_factory):
        """Test basic functionality."""
        mock_client = Mock()
        mock_client.service.RetrieveFilersSubmissionDateTime.return_value = [
            {"ID_RSSD": "123456", "DateTime": "12/31/2023 11:59:59 PM"},
            {"ID_RSSD": "789012", "DateTime": "12/30/2023 10:30:00 AM"},
        ]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_filers_submission_date_time(
            session=session,
            creds=creds,
            since_date="2023-12-01",
            reporting_period="2023-12-31",
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["rssd"] == "123456"
        assert result[0]["datetime"] == "12/31/2023 11:59:59 PM"

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_filers_submission_date_time_python_format(
        self, mock_client_factory
    ):
        """Test python datetime format output."""
        mock_client = Mock()
        mock_client.service.RetrieveFilersSubmissionDateTime.return_value = [
            {"ID_RSSD": "123456", "DateTime": "12/31/2023 11:59:59 PM"}
        ]
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_filers_submission_date_time(
            session=session,
            creds=creds,
            since_date="2023-12-01",
            reporting_period="2023-12-31",
            date_output_format="python_format",
        )

        assert isinstance(result[0]["datetime"], datetime)
        assert result[0]["datetime"].tzinfo is not None  # Should be timezone-aware


class TestCollectFilersOnReportingPeriod:
    """Test collect_filers_on_reporting_period function."""

    @patch("ffiec_data_connect.datahelpers._normalize_output_from_reporter_panel")
    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_filers_on_reporting_period(
        self, mock_client_factory, mock_normalize
    ):
        """Test basic functionality."""
        mock_raw_data = [{"some": "raw_data_1"}, {"some": "raw_data_2"}]

        mock_normalized_data = [
            {"id_rssd": "123456", "name": "Test Bank 1"},
            {"id_rssd": "789012", "name": "Test Bank 2"},
        ]

        mock_client = Mock()
        mock_client.service.RetrievePanelOfReporters.return_value = mock_raw_data
        mock_client_factory.return_value = mock_client
        mock_normalize.side_effect = mock_normalized_data

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        result = collect_filers_on_reporting_period(
            session=session, creds=creds, reporting_period="2023-12-31"
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert mock_normalize.call_count == 2

        mock_client.service.RetrievePanelOfReporters.assert_called_once_with(
            dataSeries="Call", reportingPeriodEndDate="12/31/2023"
        )


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_date_conversion_edge_cases(self):
        """Test edge cases in date conversion."""
        # Test leap year
        result = _create_ffiec_date_from_datetime(datetime(2024, 2, 29))
        assert result == "2/29/2024"

        # Test single digit month/day
        result = _create_ffiec_date_from_datetime(datetime(2023, 1, 1))
        assert result == "1/1/2023"

    def test_quarter_conversion_edge_cases(self):
        """Test edge cases in quarter conversion."""
        # The function returns None for invalid quarters that don't match regex
        result = _convert_quarter_to_date(
            "5Q2023"
        )  # Invalid quarter - doesn't match regex [1-4]
        assert result is None

        result = _convert_quarter_to_date(
            "0Q2023"
        )  # Invalid quarter - doesn't match regex [1-4]
        assert result is None

        result = _convert_quarter_to_date("invalid")  # Completely invalid
        assert result is None

    @patch("ffiec_data_connect.methods._client_factory")
    def test_collect_data_client_exception(self, mock_client_factory):
        """Test handling of client exceptions in collect_data."""
        mock_client = Mock()
        mock_client.service.RetrieveFacsimile.side_effect = Exception("Network error")
        mock_client_factory.return_value = mock_client

        session = Mock(spec=requests.Session)
        creds = Mock(spec=WebserviceCredentials)

        with pytest.raises(Exception):
            collect_data(session, creds, "2023-12-31", "123456", "call")


class TestConcurrentAccess:
    """Test thread safety and concurrent access patterns."""

    def test_date_utilities_thread_safety(self):
        """Test that date utilities are thread-safe."""
        import queue
        import threading

        results = queue.Queue()
        errors = queue.Queue()

        def convert_dates():
            try:
                for i in range(100):
                    # Test various date conversions
                    date_obj = datetime(2023, 12, 31)
                    result1 = _create_ffiec_date_from_datetime(date_obj)
                    result2 = _convert_any_date_to_ffiec_format("2023-12-31")
                    result3 = _convert_quarter_to_date("4Q2023")

                    results.put((result1, result2, result3))
            except Exception as e:
                errors.put(str(e))

        # Run conversions concurrently
        threads = []
        for _ in range(10):
            t = threading.Thread(target=convert_dates)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Check for errors
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"

        # Check results consistency
        all_results = []
        while not results.empty():
            all_results.append(results.get())

        # All results should be identical for the same inputs
        assert len(all_results) == 1000  # 10 threads * 100 iterations
        for result in all_results:
            assert result[0] == "12/31/2023"
            assert result[1] == "12/31/2023"
            assert result[2] == datetime(2023, 12, 31)

    @patch("ffiec_data_connect.methods._client_factory")
    def test_validators_thread_safety(self, mock_client_factory):
        """Test that validators are thread-safe."""
        import threading

        errors = []

        def validate_inputs():
            try:
                for _ in range(100):
                    # Test various validations
                    _output_type_validator("list")
                    _date_format_validator("string_original")
                    _validate_rssd_id("123456")

                    # Test some that should fail
                    try:
                        _validate_rssd_id("invalid")
                    except:
                        pass

            except Exception as e:
                errors.append(str(e))

        # Run validations concurrently
        threads = []
        for _ in range(10):
            t = threading.Thread(target=validate_inputs)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors for valid inputs
        assert len(errors) == 0, f"Validation errors: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
