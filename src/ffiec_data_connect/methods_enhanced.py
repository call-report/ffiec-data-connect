"""Enhanced methods for REST API support

This module contains the enhanced implementations of FFIEC methods that use
the REST API when OAuth2Credentials are provided. These functions maintain
full backward compatibility with the original SOAP implementations.
"""

import logging
from datetime import datetime
from types import ModuleType
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.data_normalizer import DataNormalizer
from ffiec_data_connect.exceptions import (
    ConnectionError,
    ValidationError,
    raise_exception,
)
from ffiec_data_connect.methods import (
    _convert_any_date_to_ffiec_format,
    _create_ffiec_date_from_datetime,
    _date_format_validator,
    _is_valid_date_or_quarter,
    _output_type_validator,
)
from ffiec_data_connect.protocol_adapter import create_protocol_adapter

# Polars import - optional
pl: Optional[ModuleType]
try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None

logger = logging.getLogger(__name__)


def _normalize_pydantic_to_soap_format(pydantic_obj: Any) -> Dict[str, Any]:
    """
    Normalize REST API Pydantic model to match original SOAP field names.
    This ensures backward compatibility with existing SOAP-based code.

    Args:
        pydantic_obj: Pydantic model instance from REST API

    Returns:
        Dictionary with field names matching original SOAP implementation
    """
    if hasattr(pydantic_obj, "model_dump"):
        # Convert Pydantic model to dict
        raw_dict = pydantic_obj.model_dump()

        # Apply the same normalization as datahelpers._normalize_output_from_reporter_panel
        from ffiec_data_connect.datahelpers import _normalize_output_from_reporter_panel

        return _normalize_output_from_reporter_panel(raw_dict)
    else:
        # Already a dict, just normalize it
        from ffiec_data_connect.datahelpers import _normalize_output_from_reporter_panel

        return _normalize_output_from_reporter_panel(pydantic_obj)


def _format_datetime_for_output(dt_str: str, date_output_format: str) -> str:
    """Format datetime string according to requested output format

    Args:
        dt_str: DateTime string from REST API
        date_output_format: Requested output format

    Returns:
        Formatted datetime string
    """
    if not dt_str:
        return dt_str

    # For now, return as-is since REST API provides consistent format
    # Future enhancement: parse and reformat according to date_output_format
    return dt_str


def collect_reporting_periods_enhanced(
    session: Union[object, None],
    creds: "OAuth2Credentials",  # Forward reference to avoid circular imports
    series: str = "call",
    output_type: str = "list",
    date_output_format: str = "string_original",
) -> Union[List[str], pd.DataFrame, Any]:
    """Enhanced REST implementation for collect_reporting_periods

    Args:
        session: Session object (not used for REST API)
        creds: OAuth2Credentials instance
        series: Data series ("call" or "ubpr")
        output_type: Output format ("list", "pandas", or "polars")
        date_output_format: Date format for output

    Returns:
        List of reporting periods or DataFrame in ascending chronological order (oldest first)
    """
    logger.debug(f"collect_reporting_periods_enhanced called with series={series}")

    # Validate inputs
    _output_type_validator(output_type)
    _date_format_validator(date_output_format)

    try:
        # Create protocol adapter
        adapter = create_protocol_adapter(creds, session)  # type: ignore[arg-type]

        # Call appropriate REST endpoint
        if series.lower() == "call":
            raw_periods = adapter.retrieve_reporting_periods("Call")
        elif series.lower() == "ubpr":
            raw_periods = adapter.retrieve_ubpr_reporting_periods()
        else:
            raise_exception(
                ValidationError,
                f"Invalid series: {series}",
                field="series",
                value=series,
                expected="'call' or 'ubpr'",
            )

        logger.debug(
            f"Retrieved and validated {len(raw_periods)} reporting periods via REST API"
        )

        # Validate that we received properly formatted data
        validation_report = DataNormalizer.validate_pydantic_compatibility(
            raw_periods,
            (
                "RetrieveUBPRReportingPeriods"
                if series.lower() == "ubpr"
                else "RetrieveReportingPeriods"
            ),
        )

        if not validation_report["compatible"]:
            logger.warning(
                f"Schema validation warnings: {validation_report['warnings']}"
            )

        # Sort reporting periods in ascending chronological order (oldest first)
        from .utils import sort_reporting_periods_ascending

        sorted_periods = sort_reporting_periods_ascending(raw_periods)

        # Process dates - convert from MM/DD/YYYY to requested format if needed
        processed_periods = []
        for period_str in sorted_periods:
            # For now, keep as-is since most users expect MM/DD/YYYY
            # Future enhancement: convert based on date_output_format
            processed_periods.append(period_str)

        # Handle output type conversion
        if output_type == "pandas":
            return pd.DataFrame({"reporting_period": processed_periods})
        elif output_type == "polars" and POLARS_AVAILABLE:
            return pl.DataFrame({"reporting_period": processed_periods})  # type: ignore[union-attr]
        else:
            return processed_periods

    except Exception as e:
        logger.error(f"REST API call failed in collect_reporting_periods_enhanced: {e}")
        raise_exception(
            ConnectionError, f"Failed to retrieve reporting periods via REST API: {e}"
        )


def collect_filers_on_reporting_period_enhanced(
    session: Union[object, None],
    creds: "OAuth2Credentials",  # Forward reference to avoid circular imports
    reporting_period: Union[str, datetime],
    output_type: str = "list",
) -> Union[List[Dict[str, Any]], pd.DataFrame]:
    """Enhanced REST implementation for collect_filers_on_reporting_period

    Args:
        session: Session object (not used for REST API)
        creds: OAuth2Credentials instance
        reporting_period: Reporting period date
        output_type: Output format ("list", "pandas", or "polars")

    Returns:
        List of filer dictionaries or DataFrame containing:
        - "rssd"/"id_rssd": Institution RSSD ID (both field names provided for compatibility)
        - Other filer fields as documented in main function

        NOTE: Property names were inconsistent in earlier code, so both 'rssd' and 'id_rssd'
        are provided with identical data to reduce need to refactor existing user code.
    """
    logger.debug(
        f"collect_filers_on_reporting_period_enhanced called for period={reporting_period}"
    )

    # Validate inputs
    _output_type_validator(output_type)

    # Validate and convert reporting period
    if not _is_valid_date_or_quarter(reporting_period):
        raise_exception(
            ValidationError,
            "Invalid reporting period format",
            field="reporting_period",
            value=str(reporting_period),
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    # Convert to FFIEC format
    ffiec_date: Optional[str]
    if isinstance(reporting_period, datetime):
        ffiec_date = _create_ffiec_date_from_datetime(reporting_period)
    else:
        ffiec_date = _convert_any_date_to_ffiec_format(reporting_period)
        if ffiec_date is None:
            raise_exception(
                ValidationError,
                "Could not convert reporting period to FFIEC format",
                field="reporting_period",
                value=str(reporting_period),
                expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
            )

    try:
        # Create protocol adapter and call REST endpoint
        assert ffiec_date is not None  # Already checked above
        adapter = create_protocol_adapter(creds, session)  # type: ignore[arg-type]
        normalized_filers = adapter.retrieve_panel_of_reporters(ffiec_date)

        logger.debug(f"Retrieved {len(normalized_filers)} filers")

        # Convert Pydantic models to SOAP-compatible format
        if normalized_filers and hasattr(normalized_filers[0], "model_dump"):
            # Apply the same normalization as original SOAP implementation
            normalized_filers = [
                _normalize_pydantic_to_soap_format(filer) for filer in normalized_filers
            ]

        # Handle output type conversion
        if output_type == "pandas":
            return pd.DataFrame(normalized_filers)
        elif output_type == "polars" and POLARS_AVAILABLE:
            return pl.DataFrame(normalized_filers)  # type: ignore[union-attr]
        else:
            return normalized_filers

    except Exception as e:
        logger.error(
            f"REST API call failed in collect_filers_on_reporting_period_enhanced: {e}"
        )
        raise_exception(ConnectionError, f"Failed to retrieve filers via REST API: {e}")


def collect_filers_since_date_enhanced(
    session: Union[object, None],
    creds: "OAuth2Credentials",  # Forward reference to avoid circular imports
    reporting_period: Union[str, datetime],
    since_date: Union[str, datetime],
    output_type: str = "list",
) -> Union[List[str], pd.DataFrame]:
    """Enhanced REST implementation for collect_filers_since_date

    Args:
        session: Session object (not used for REST API)
        creds: OAuth2Credentials instance
        reporting_period: Reporting period date
        since_date: Date to check for filings since
        output_type: Output format ("list", "pandas", or "polars")

    Returns:
        List of RSSD IDs or DataFrame
    """
    logger.debug(
        f"collect_filers_since_date_enhanced called for period={reporting_period}, since={since_date}"
    )

    # Validate inputs
    _output_type_validator(output_type)

    # Validate reporting period
    if not _is_valid_date_or_quarter(reporting_period):
        raise_exception(
            ValidationError,
            "Invalid reporting period format",
            field="reporting_period",
            value=str(reporting_period),
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    # Validate since_date
    if not _is_valid_date_or_quarter(since_date):
        raise_exception(
            ValidationError,
            "Invalid since_date format",
            field="since_date",
            value=str(since_date),
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    # Convert dates to FFIEC format
    ffiec_reporting_period: Optional[str]
    ffiec_since_date: Optional[str]
    if isinstance(reporting_period, datetime):
        ffiec_reporting_period = _create_ffiec_date_from_datetime(reporting_period)
    else:
        ffiec_reporting_period = _convert_any_date_to_ffiec_format(reporting_period)

    if isinstance(since_date, datetime):
        ffiec_since_date = _create_ffiec_date_from_datetime(since_date)
    else:
        ffiec_since_date = _convert_any_date_to_ffiec_format(since_date)

    if ffiec_reporting_period is None or ffiec_since_date is None:
        raise_exception(
            ValidationError,
            "Could not convert dates to FFIEC format",
            field="dates",
            value=f"reporting_period={reporting_period}, since_date={since_date}",
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    try:
        # Create protocol adapter and call REST endpoint
        assert ffiec_reporting_period is not None  # Already checked above
        assert ffiec_since_date is not None  # Already checked above
        adapter = create_protocol_adapter(creds, session)  # type: ignore[arg-type]
        rssd_ids = adapter.retrieve_filers_since_date(
            ffiec_reporting_period, ffiec_since_date
        )

        logger.debug(f"Retrieved {len(rssd_ids)} RSSD IDs")

        # Ensure RSSD IDs are strings (preserve data integrity)
        string_rssd_ids = [str(rssd_id) for rssd_id in rssd_ids]

        # Handle output type conversion
        if output_type == "pandas":
            # Provide dual column names for compatibility
            df = pd.DataFrame({"rssd_id": string_rssd_ids})
            df["rssd"] = df["rssd_id"]  # Dual field support
            return df
        elif output_type == "polars" and POLARS_AVAILABLE:
            # Provide dual column names for compatibility
            data_dict = {"rssd_id": string_rssd_ids, "rssd": string_rssd_ids}
            return pl.DataFrame(data_dict)  # type: ignore[union-attr]
        else:
            return string_rssd_ids

    except Exception as e:
        logger.error(f"REST API call failed in collect_filers_since_date_enhanced: {e}")
        raise_exception(
            ConnectionError, f"Failed to retrieve filers since date via REST API: {e}"
        )


def collect_filers_submission_date_time_enhanced(
    session: Union[object, None],
    creds: "OAuth2Credentials",  # Forward reference to avoid circular imports
    since_date: Union[str, datetime],
    reporting_period: Union[str, datetime],
    output_type: str = "list",
    date_output_format: str = "string_original",
) -> Union[List[Dict[str, Any]], pd.DataFrame, Any]:
    """Enhanced REST implementation for collect_filers_submission_date_time

    Args:
        session: Session object (not used for REST API)
        creds: OAuth2Credentials instance
        since_date: Date to check for submissions since
        reporting_period: Reporting period date
        date_output_format: Format for output dates
        output_type: Output format ("list", "pandas", or "polars")

    Returns:
        List of submission dictionaries or DataFrame
    """
    logger.debug(
        f"collect_filers_submission_date_time_enhanced called for period={reporting_period}, since={since_date}"
    )

    # Validate inputs
    _output_type_validator(output_type)
    _date_format_validator(date_output_format)

    # Validate dates
    if not _is_valid_date_or_quarter(reporting_period):
        raise_exception(
            ValidationError,
            "Invalid reporting period format",
            field="reporting_period",
            value=str(reporting_period),
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    if not _is_valid_date_or_quarter(since_date):
        raise_exception(
            ValidationError,
            "Invalid since_date format",
            field="since_date",
            value=str(since_date),
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    # Convert dates to FFIEC format
    ffiec_reporting_period: Optional[str]
    ffiec_since_date: Optional[str]
    if isinstance(reporting_period, datetime):
        ffiec_reporting_period = _create_ffiec_date_from_datetime(reporting_period)
    else:
        ffiec_reporting_period = _convert_any_date_to_ffiec_format(reporting_period)

    if isinstance(since_date, datetime):
        ffiec_since_date = _create_ffiec_date_from_datetime(since_date)
    else:
        ffiec_since_date = _convert_any_date_to_ffiec_format(since_date)

    if ffiec_reporting_period is None or ffiec_since_date is None:
        raise_exception(
            ValidationError,
            "Could not convert dates to FFIEC format",
            field="dates",
            value=f"reporting_period={reporting_period}, since_date={since_date}",
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    try:
        # Create protocol adapter and call REST endpoint
        assert ffiec_reporting_period is not None  # Already checked above
        assert ffiec_since_date is not None  # Already checked above
        adapter = create_protocol_adapter(creds, session)  # type: ignore[arg-type]
        submissions = adapter.retrieve_filers_submission_datetime(
            ffiec_reporting_period, ffiec_since_date
        )

        logger.debug(f"Retrieved {len(submissions)} submission records")

        # Process submission data to match original SOAP format
        processed_submissions = []
        for submission in submissions:
            # Handle both dict and Pydantic model objects
            if hasattr(submission, "ID_RSSD"):
                # It's a Pydantic model object - provide both field names for compatibility
                rssd_value = str(submission.ID_RSSD)
                processed_sub = {
                    "rssd": rssd_value,  # Institution RSSD ID
                    "id_rssd": rssd_value,  # Institution RSSD ID (same data, dual field support)
                    "datetime": _format_datetime_for_output(
                        submission.DateTime,  # type: ignore[attr-defined]
                        date_output_format,
                    ),
                }
            else:
                # It's a dictionary - provide both field names for compatibility
                rssd_value = str(submission.get("ID_RSSD", ""))
                processed_sub = {
                    "rssd": rssd_value,  # Institution RSSD ID
                    "id_rssd": rssd_value,  # Institution RSSD ID (same data, dual field support)
                    "datetime": _format_datetime_for_output(
                        submission.get("DateTime", ""), date_output_format
                    ),
                }
            processed_submissions.append(processed_sub)

        # Handle output type conversion
        if output_type == "pandas":
            return pd.DataFrame(processed_submissions)
        elif output_type == "polars" and POLARS_AVAILABLE:
            return pl.DataFrame(processed_submissions)  # type: ignore[union-attr]
        else:
            return processed_submissions

    except Exception as e:
        logger.error(
            f"REST API call failed in collect_filers_submission_date_time_enhanced: {e}"
        )
        raise_exception(
            ConnectionError,
            f"Failed to retrieve submission date times via REST API: {e}",
        )
