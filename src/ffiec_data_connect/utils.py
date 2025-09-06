"""Utility functions for FFIEC Data Connect library."""

import re
from datetime import datetime
from typing import List

# Date format regex patterns (imported from methods.py to avoid dependency)
yyyymmddDashRegex = r"^\d{4}-\d{2}-\d{2}$"
mmddyyyyRegex = r"^\d{1,2}/\d{1,2}/\d{4}$"


def sort_reporting_periods_ascending(periods: List[str]) -> List[str]:
    """Sort reporting periods in ascending chronological order (oldest first).

    Handles both SOAP format (YYYY-MM-DD) and REST format (MM/DD/YYYY).
    Preserves the original format after sorting.

    Args:
        periods: List of date strings to sort

    Returns:
        List of date strings sorted in ascending chronological order

    Example:
        >>> periods = ["2023-12-31", "2022-06-30", "2023-03-31"]
        >>> sort_reporting_periods_ascending(periods)
        ["2022-06-30", "2023-03-31", "2023-12-31"]
    """
    if not periods:
        return periods

    if len(periods) == 1:
        return periods

    # Detect format from first period
    first_period = periods[0]
    is_soap_format = bool(re.match(yyyymmddDashRegex, first_period))
    is_rest_format = bool(re.match(mmddyyyyRegex, first_period))

    if not (is_soap_format or is_rest_format):
        # If format is not recognized, return original list unsorted
        return periods

    # Verify all periods use the same format
    for period in periods:
        period_is_soap = bool(re.match(yyyymmddDashRegex, period))
        period_is_rest = bool(re.match(mmddyyyyRegex, period))

        if is_soap_format and not period_is_soap:
            # Mixed formats - return original list unsorted
            return periods
        elif is_rest_format and not period_is_rest:
            # Mixed formats - return original list unsorted
            return periods

    # Parse dates to datetime objects for proper sorting
    parsed_dates = []
    try:
        for period in periods:
            if is_soap_format:
                # Parse SOAP format: YYYY-MM-DD
                dt = datetime.strptime(period, "%Y-%m-%d")
            else:
                # Parse REST format: MM/DD/YYYY
                dt = datetime.strptime(period, "%m/%d/%Y")
            parsed_dates.append((dt, period))

        # Sort by datetime (ascending = oldest first)
        parsed_dates.sort(key=lambda x: x[0])

        # Extract the original formatted strings in sorted order
        sorted_periods = [period for _, period in parsed_dates]
        return sorted_periods

    except ValueError:
        # If parsing fails, return original list unsorted
        return periods

