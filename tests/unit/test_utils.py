"""
Unit tests for utils.py coverage.

Tests utility functions including error handling edge cases.
"""

import logging

import pytest

from ffiec_data_connect.utils import sort_reporting_periods_ascending


class TestSortReportingPeriodsCoverage:
    """Tests targeting uncovered lines in utils.py."""

    def test_unparseable_date_in_list_returns_original(self):
        """sort_reporting_periods_ascending with unparseable date logs error and returns original list (line 62)."""
        # First date matches YYYY-MM-DD format, but second is invalid and will fail strptime
        periods = ["2023-12-31", "2023-XX-31", "2022-06-30"]

        result = sort_reporting_periods_ascending(periods)

        # Should return original unsorted list when a date fails to parse
        assert result == periods

    def test_unparseable_date_logs_error(self, caplog):
        """sort_reporting_periods_ascending logs an error for unparseable dates."""
        periods = ["2023-12-31", "2023-XX-31", "2022-06-30"]

        with caplog.at_level(logging.ERROR, logger="ffiec_data_connect.utils"):
            result = sort_reporting_periods_ascending(periods)

        assert result == periods
        assert "Failed to parse reporting period" in caplog.text

    def test_inconsistent_format_in_rest_dates(self):
        """sort_reporting_periods_ascending with inconsistent REST format returns original."""
        # First date matches MM/DD/YYYY, but second doesn't
        periods = ["12/31/2023", "2023-06-30", "6/30/2022"]

        result = sort_reporting_periods_ascending(periods)

        assert result == periods

    def test_empty_list(self):
        """sort_reporting_periods_ascending with empty list returns empty list."""
        assert sort_reporting_periods_ascending([]) == []

    def test_single_item(self):
        """sort_reporting_periods_ascending with single item returns same list."""
        periods = ["2023-12-31"]
        assert sort_reporting_periods_ascending(periods) == periods

    def test_unknown_format_returns_unsorted(self):
        """sort_reporting_periods_ascending with unknown format returns original."""
        periods = ["not-a-date", "also-not"]
        result = sort_reporting_periods_ascending(periods)
        assert result == periods


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
