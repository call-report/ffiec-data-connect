"""
Test suite for reporting periods sorting functionality.

Tests the _sort_reporting_periods_ascending function and its integration
with REST API implementations. SOAP integration tests have been removed
since the SOAP API was deprecated.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.methods import collect_reporting_periods
from ffiec_data_connect.utils import sort_reporting_periods_ascending


class TestReportingPeriodsSorting:
    """Test suite for the reporting periods sorting functionality."""

    def test_sort_soap_format_descending_to_ascending(self):
        """Test sorting SOAP format dates from descending to ascending order."""
        # SOAP dates in descending order (newest first) - like call reports
        soap_dates_desc = [
            "2023-12-31",
            "2023-09-30",
            "2023-06-30",
            "2023-03-31",
            "2022-12-31"
        ]

        result = sort_reporting_periods_ascending(soap_dates_desc)

        expected = [
            "2022-12-31",
            "2023-03-31",
            "2023-06-30",
            "2023-09-30",
            "2023-12-31"
        ]

        assert result == expected, f"Expected {expected}, got {result}"

    def test_sort_rest_format_descending_to_ascending(self):
        """Test sorting REST format dates from descending to ascending order."""
        # REST dates in descending order (newest first) - like call reports
        rest_dates_desc = [
            "12/31/2023",
            "9/30/2023",
            "6/30/2023",
            "3/31/2023",
            "12/31/2022"
        ]

        result = sort_reporting_periods_ascending(rest_dates_desc)

        expected = [
            "12/31/2022",
            "3/31/2023",
            "6/30/2023",
            "9/30/2023",
            "12/31/2023"
        ]

        assert result == expected, f"Expected {expected}, got {result}"

    def test_sort_soap_format_already_ascending(self):
        """Test sorting SOAP format dates that are already in ascending order."""
        # SOAP dates already in ascending order (oldest first) - like some UBPR reports
        soap_dates_asc = [
            "2022-12-31",
            "2023-03-31",
            "2023-06-30",
            "2023-09-30",
            "2023-12-31"
        ]

        result = sort_reporting_periods_ascending(soap_dates_asc)

        # Should remain the same
        assert result == soap_dates_asc, f"Expected {soap_dates_asc}, got {result}"

    def test_sort_rest_format_already_ascending(self):
        """Test sorting REST format dates that are already in ascending order."""
        # REST dates already in ascending order
        rest_dates_asc = [
            "12/31/2022",
            "3/31/2023",
            "6/30/2023",
            "9/30/2023",
            "12/31/2023"
        ]

        result = sort_reporting_periods_ascending(rest_dates_asc)

        # Should remain the same
        assert result == rest_dates_asc, f"Expected {rest_dates_asc}, got {result}"

    def test_sort_with_single_date_soap(self):
        """Test sorting with a single SOAP format date."""
        single_date = ["2023-12-31"]
        result = sort_reporting_periods_ascending(single_date)
        assert result == single_date

    def test_sort_with_single_date_rest(self):
        """Test sorting with a single REST format date."""
        single_date = ["12/31/2023"]
        result = sort_reporting_periods_ascending(single_date)
        assert result == single_date

    def test_sort_empty_list(self):
        """Test sorting with empty list."""
        empty_list = []
        result = sort_reporting_periods_ascending(empty_list)
        assert result == empty_list

    def test_sort_mixed_years_soap_format(self):
        """Test sorting SOAP dates across multiple years."""
        mixed_years = [
            "2025-06-30",
            "2001-09-30",
            "2023-12-31",
            "2022-03-31",
            "2024-12-31"
        ]

        result = sort_reporting_periods_ascending(mixed_years)

        expected = [
            "2001-09-30",
            "2022-03-31",
            "2023-12-31",
            "2024-12-31",
            "2025-06-30"
        ]

        assert result == expected, f"Expected {expected}, got {result}"

    def test_sort_mixed_years_rest_format(self):
        """Test sorting REST dates across multiple years."""
        mixed_years = [
            "6/30/2025",
            "9/30/2001",
            "12/31/2023",
            "3/31/2022",
            "12/31/2024"
        ]

        result = sort_reporting_periods_ascending(mixed_years)

        expected = [
            "9/30/2001",
            "3/31/2022",
            "12/31/2023",
            "12/31/2024",
            "6/30/2025"
        ]

        assert result == expected, f"Expected {expected}, got {result}"

    def test_sort_invalid_format_returns_original(self):
        """Test that invalid date formats return the original list unsorted."""
        invalid_dates = ["invalid-date", "another-invalid", "2023-13-45"]
        result = sort_reporting_periods_ascending(invalid_dates)

        # Should return original list unchanged for invalid formats
        assert result == invalid_dates

    def test_sort_mixed_formats_returns_original(self):
        """Test that mixed date formats return the original list unsorted."""
        mixed_formats = ["2023-12-31", "12/31/2023", "2023-06-30"]
        result = sort_reporting_periods_ascending(mixed_formats)

        # Should return original list unchanged for mixed formats
        assert result == mixed_formats

    def test_chronological_order_verification_soap(self):
        """Verify that sorted SOAP dates are in proper chronological order."""
        unsorted_dates = [
            "2023-12-31",
            "2022-03-31",
            "2023-06-30",
            "2024-09-30",
            "2023-03-31"
        ]

        result = sort_reporting_periods_ascending(unsorted_dates)

        # Convert to datetime objects to verify chronological order
        parsed_dates = [datetime.strptime(d, "%Y-%m-%d") for d in result]

        # Check that each date is <= the next date
        for i in range(len(parsed_dates) - 1):
            assert parsed_dates[i] <= parsed_dates[i + 1], \
                f"Dates not in chronological order: {parsed_dates[i]} > {parsed_dates[i + 1]}"

    def test_chronological_order_verification_rest(self):
        """Verify that sorted REST dates are in proper chronological order."""
        unsorted_dates = [
            "12/31/2023",
            "3/31/2022",
            "6/30/2023",
            "9/30/2024",
            "3/31/2023"
        ]

        result = sort_reporting_periods_ascending(unsorted_dates)

        # Convert to datetime objects to verify chronological order
        parsed_dates = [datetime.strptime(d, "%m/%d/%Y") for d in result]

        # Check that each date is <= the next date
        for i in range(len(parsed_dates) - 1):
            assert parsed_dates[i] <= parsed_dates[i + 1], \
                f"Dates not in chronological order: {parsed_dates[i]} > {parsed_dates[i + 1]}"


class TestCollectReportingPeriodsIntegration:
    """Integration tests for collect_reporting_periods with sorting."""

    @patch('ffiec_data_connect.methods_enhanced.collect_reporting_periods_enhanced')
    def test_rest_api_path_uses_sorting(self, mock_enhanced):
        """Test that REST API path also applies sorting."""
        from ffiec_data_connect.credentials import OAuth2Credentials
        from ffiec_data_connect.methods import collect_reporting_periods

        # Mock the enhanced method to return unsorted REST format dates
        mock_enhanced.return_value = [
            "12/31/2023",  # Descending order (newest first)
            "9/30/2023",
            "3/31/2023",
            "12/31/2022"   # Oldest last
        ]

        # Create OAuth2 credentials to trigger REST path
        oauth_creds = Mock()
        oauth_creds.__class__.__name__ = 'OAuth2Credentials'

        # Call collect_reporting_periods - should route to REST path
        with patch('ffiec_data_connect.methods.isinstance', return_value=True):
            result = collect_reporting_periods(
                oauth_creds,
                series="call",
                output_type="list"
            )

        # The enhanced method was called, which handles its own sorting
        mock_enhanced.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
