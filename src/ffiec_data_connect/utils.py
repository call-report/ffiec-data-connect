"""Utility functions for FFIEC Data Connect library."""

import logging
import re
from datetime import datetime
from typing import List

# Set up logging
logger = logging.getLogger(__name__)

# Date format regex patterns (defined locally to avoid dependency on methods.py)
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
        logger.warning(f"Unknown date format in reporting periods: {first_period}")
        return periods  # Return unsorted if format is unknown

    # Parse dates to datetime objects for proper sorting
    parsed_dates = []
    for period in periods:
        try:
            if is_soap_format:
                # SOAP format: YYYY-MM-DD
                if not re.match(yyyymmddDashRegex, period):
                    raise ValueError(
                        f"Inconsistent date format: expected YYYY-MM-DD, got {period}"
                    )
                dt = datetime.strptime(period, "%Y-%m-%d")
            else:
                # REST format: MM/DD/YYYY
                if not re.match(mmddyyyyRegex, period):
                    raise ValueError(
                        f"Inconsistent date format: expected MM/DD/YYYY, got {period}"
                    )
                dt = datetime.strptime(period, "%m/%d/%Y")

            parsed_dates.append((dt, period))
        except ValueError as e:
            logger.error(f"Failed to parse reporting period '{period}': {e}")
            # Return original unsorted list if any date fails to parse
            return periods

    # Sort by datetime (ascending = oldest first)
    parsed_dates.sort(key=lambda x: x[0])

    # Extract the original formatted strings in sorted order
    sorted_periods = [period for _, period in parsed_dates]

    logger.debug(f"Sorted {len(periods)} reporting periods in ascending order")
    return sorted_periods
