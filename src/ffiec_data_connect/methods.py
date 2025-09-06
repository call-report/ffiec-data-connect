"""Methods that wrap the FFIEC Webservice API

The methods contained in this module are utilized to call and collect data from the FFIEC Webservice API.

"""

import logging
import re
from datetime import datetime
from typing import Any, List, Optional, Union
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

# Polars import - optional for direct XBRL to polars conversion
try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None  # type: ignore

from zeep import Client

from ffiec_data_connect import (
    credentials,
    datahelpers,
    ffiec_connection,
    xbrl_processor,
)

# Import OAuth2Credentials for type annotations
from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.exceptions import (
    ConnectionError,
    NoDataError,
    ValidationError,
    raise_exception,
)
from ffiec_data_connect.utils import sort_reporting_periods_ascending

# Set up logging
logger = logging.getLogger(__name__)

# global date regex
quarterStringRegex = r"^[1-4](q|Q)([0-9]{4})$"
yyyymmddRegex = r"^[0-9]{4}[0-9]{2}[0-9]{2}$"
yyyymmddDashRegex = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
mmddyyyyRegex = r"^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$"

validRegexList = [quarterStringRegex, yyyymmddRegex, yyyymmddDashRegex, mmddyyyyRegex]


def _create_ffiec_date_from_datetime(indate: datetime) -> str:
    """Converts a datetime object to a FFIEC-formatted date

    Args:
        indate (datetime): the date to convert

    Returns:
        str: the date in FFIEC format
    """
    month_str = str(indate.month)
    day_str = str(indate.day)
    year_str = str(indate.year)

    mmddyyyy = month_str + "/" + day_str + "/" + year_str

    return mmddyyyy


def _convert_any_date_to_ffiec_format(indate: Union[str, datetime]) -> Optional[str]:
    """Converts a string-based date or python datetime object to a FFIEC-formatted date

    Args:
        date (str or datetime): the date to convert. This can be a string in the format of "YYYY-MM-DD", "YYYYMMDD", "MM/DD/YYYY", or a python datetime object

    Returns:
        str: the date in FFIEC format
    """

    if isinstance(indate, datetime):
        return _create_ffiec_date_from_datetime(indate)
    elif isinstance(indate, str):
        # does the date have two slashes?
        if indate.count("-") == 2:
            return _create_ffiec_date_from_datetime(
                datetime.strptime(indate, "%Y-%m-%d")
            )
        elif indate.count("/") == 2:
            return _create_ffiec_date_from_datetime(
                datetime.strptime(indate, "%m/%d/%Y")
            )
        elif len(indate) == 8:
            return _create_ffiec_date_from_datetime(datetime.strptime(indate, "%Y%m%d"))
        else:
            # String format not recognized - return None for backwards compatibility
            return None
    else:
        # raise an error if we don't have a valid date
        raise ValueError(
            "Invalid date format. Must be a string in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object"
        )


def _convert_quarter_to_date(reporting_period: str) -> Optional[datetime]:
    """Converts date in the format of #QYYYY to a datetime object

    Returns:
        _type_: _description_
    """

    # convert the reporting period to a datetime object
    if re.search(quarterStringRegex, reporting_period):
        # the reporting period is a quarter string
        # get the quarter number
        quarter_number = int(reporting_period[0])
        # get the year
        year = int(reporting_period[-4:])

        if quarter_number == 1:
            # first quarter
            return datetime(year, 3, 31)
        elif quarter_number == 2:
            return datetime(year, 6, 30)
        elif quarter_number == 3:
            return datetime(year, 9, 30)
        elif quarter_number == 4:
            return datetime(year, 12, 31)
        else:
            return (
                None  # Invalid quarter number - return None for backwards compatibility
            )
    else:
        return None  # Invalid reporting period format - return None for backwards compatibility


def _is_valid_date_or_quarter(reporting_period: Union[str, datetime]) -> bool:
    """Validates the reporting period input argument, which should indicate either the name of a calendar quarter, or a string that represents the last day of a quarter (e.g. "2019-03-31"), or a datetime object.

    If reporting period is a datetime, validate that the date is at quarter end.

    If reporting period is a string, validate that the string is in the format of "Q#-YYYY", "Q#-YY", "YYYY-MM-DD", "YYYYMMDD", or m/d/YYYY, or m/d/YY.

    Args:
        reporting_period (str or datetime): the reporting period to validate

    Returns:
        bool: True if valid reporting period, False if not valid reporting period

    """

    if isinstance(reporting_period, datetime):
        # what is the month of the quarter?
        month = reporting_period.month  # 1 = Jan, 12= Dec
        day = reporting_period.day  # 1 = 1st

        if month in [3, 12]:
            if day == 31:
                return True  # the quarter ends on the 31st in March and December
            else:
                return False
        elif month in [6, 9]:
            if day == 30:
                return True  # the quarter ends on the 30th in June, September
            else:
                return False
        else:
            return False  # not a valid quarter end month
    elif isinstance(reporting_period, str):
        # does our date match any of the valid regexes?
        return any(re.search(regex, reporting_period) for regex in validRegexList)
    else:
        return (
            False  # we don't know what to do with this type of input, so return false
        )


def _return_ffiec_reporting_date(indate: Union[datetime, str]) -> str:
    if isinstance(indate, datetime):
        return _create_ffiec_date_from_datetime(indate)
    elif isinstance(indate, str):
        if indate[1] == "Q":
            quarter_date = _convert_quarter_to_date(indate)
            if quarter_date is None:
                raise ValueError(
                    "Invalid quarter format. Must be in the format #Qyyyy where # is 1-4"
                )
            return _create_ffiec_date_from_datetime(quarter_date)
        else:
            ffiec_date = _convert_any_date_to_ffiec_format(indate)
            if ffiec_date is None:
                raise ValueError(
                    "Invalid date format. Must be a string in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object"
                )

            ffiec_date_month = ffiec_date.split("/")[0]
            ffiec_date_date = ffiec_date.split("/")[1]

            if (
                ffiec_date_month == "3" or ffiec_date_month == "03"
            ) and ffiec_date_date == "31":
                return ffiec_date
            elif (
                ffiec_date_month == "6" or ffiec_date_month == "06"
            ) and ffiec_date_date == "30":
                return ffiec_date
            elif (
                ffiec_date_month == "9" or ffiec_date_month == "09"
            ) and ffiec_date_date == "30":
                return ffiec_date
            elif ffiec_date_month == "12" and ffiec_date_date == "31":
                return ffiec_date
            else:
                raise ValueError(
                    "Invalid date format. Must be a string in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object"
                )


def _output_type_validator(output_type: str) -> bool:
    """Internal function to validate the output_type

    Args:
        output_type (str): the output_type to validate

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If output_type is invalid
    """
    valid_types = ["list", "pandas", "polars", "bytes"]
    if output_type not in valid_types:
        raise_exception(
            ValidationError,
            f"Invalid output_type: {output_type}",
            field="output_type",
            value=output_type,
            expected=f"one of {valid_types}",
        )
    return True


def _date_format_validator(date_format: str) -> bool:
    """Internal function to validate the date_format

    Args:
        date_format (str): the date_format to validate

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If date_format is invalid
    """
    valid_formats = ["string_original", "string_yyyymmdd", "python_format"]
    if date_format not in valid_formats:
        raise_exception(
            ValidationError,
            f"Invalid date_format: {date_format}",
            field="date_format",
            value=date_format,
            expected=f"one of {valid_formats}",
        )
    return True


def _credentials_validator(
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
) -> bool:
    """Internal function to validate the credentials

    Args:
        creds: Either WebserviceCredentials or OAuth2Credentials

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If credentials are invalid
    """
    from .credentials import OAuth2Credentials

    if not isinstance(creds, (credentials.WebserviceCredentials, OAuth2Credentials)):
        raise_exception(
            ValidationError,
            "Invalid credentials type",
            field="credentials",
            value=type(creds).__name__,
            expected="WebserviceCredentials or OAuth2Credentials instance",
        )
    return True


def _session_validator(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
) -> bool:
    """Internal function to validate the session

    Args:
        session: The session to validate (can be None for REST API)

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If session is invalid
    """
    # Allow None for REST API usage
    if session is None:
        return True
    elif isinstance(session, ffiec_connection.FFIECConnection):
        return True
    elif isinstance(session, requests.Session):
        return True
    else:
        raise_exception(
            ValidationError,
            "Invalid session type",
            field="session",
            value=type(session).__name__,
            expected="requests.Session or FFIECConnection instance",
        )


def _validate_rssd_id(rssd_id: str) -> int:
    """Validate and convert RSSD ID to integer.

    Args:
        rssd_id: The RSSD ID to validate

    Returns:
        int: Valid RSSD ID as integer

    Raises:
        ValidationError: If RSSD ID is invalid
    """
    if not rssd_id:
        raise_exception(
            ValidationError,
            "RSSD ID is empty",
            field="rssd_id",
            value=rssd_id,
            expected="non-empty numeric string",
        )

    # Remove any whitespace
    rssd_id = str(rssd_id).strip()

    # Check if it's numeric
    if not rssd_id.isdigit():
        raise_exception(
            ValidationError,
            f"RSSD ID must be numeric: {rssd_id}",
            field="rssd_id",
            value=rssd_id,
            expected="numeric string (digits only)",
        )

    # Convert to int and validate range
    rssd_int = int(rssd_id)
    if rssd_int <= 0 or rssd_int > 99999999:  # Max 8 digits for RSSD
        raise_exception(
            ValidationError,
            f"RSSD ID out of range: {rssd_id}",
            field="rssd_id",
            value=rssd_id,
            expected="positive integer between 1 and 99999999",
        )

    return rssd_int


def _return_client_session(
    session: requests.Session, creds: credentials.WebserviceCredentials
) -> Client:
    """Internal function to return a cached zeep client session for better performance.

    Args:
        session (requests.Session): the requests.Session object to use
        creds (credentials.WebserviceCredentials): the credentials to use

    Returns:
        Client: Cached or newly created zeep Client instance
    """

    # Use cached SOAP client for better performance and memory usage
    from ffiec_data_connect.soap_cache import get_soap_client

    return get_soap_client(creds, session)


def collect_reporting_periods(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    series: str = "call",
    output_type: str = "list",
    date_output_format: str = "string_original",
) -> Union[List[str], List[datetime], pd.Series]:
    """Returns list of reporting periods available for access via the FFIEC webservice

    **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
    For better performance, use OAuth2Credentials for REST API access.

    | Note on `date_output_format`:

    * ``string_original`` is the default output format, and is the format that is used by the FFIEC webservice: mm/dd/yyyy
    * ``string_yyyymmdd`` is the date in yyyymmdd format
    * ``python_format`` is the date in python datetime format


    Args:
        session: The session object (can be None for REST API)
        creds: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
        series (str, optional): `call` or `ubpr`
        output_type (str): `list` or `pandas`
        date_output_format: `string_original`, `string_yyyymmdd`, or `python_format`

    Returns:
        `list` or `Pandas` series: Returns a list of reporting periods from the FFIEC Webservice
        in ascending chronological order (oldest first)

    """

    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)

    # Check if we have OAuth2 credentials - use enhanced method
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        from .methods_enhanced import collect_reporting_periods_enhanced

        return collect_reporting_periods_enhanced(
            session, creds, series, output_type, date_output_format
        )

    # Original SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    # we have a session and valid credentials, so try to log in
    assert session is not None, "Session should not be None after validation for SOAP"
    client = _client_factory(session, creds)

    # scope ret outside the if statement
    ret = None

    if series == "call":
        ret = client.service.RetrieveReportingPeriods(dataSeries="Call")
    elif series == "ubpr":
        ret = client.service.RetrieveUBPRReportingPeriods()

    # did we return anything? if not, raise an error
    if ret is None or len(ret) == 0:
        raise_exception(
            NoDataError,
            "No reporting periods available",
            reporting_period=None,
            rssd_id=None,
        )

    # At this point ret is guaranteed to be non-None and non-empty
    assert ret is not None

    # Sort reporting periods in ascending chronological order (oldest first)
    ret_sorted = sort_reporting_periods_ascending(ret)
    ret_date_formatted: Union[List[str], List[datetime]] = ret_sorted

    if date_output_format == "string_yyyymmdd":
        ret_date_formatted = [
            datetime.strftime(datetime.strptime(x, "%Y-%m-%d"), "%Y%m%d")
            for x in ret_sorted
        ]
    elif date_output_format == "python_format":
        ret_date_formatted = [datetime.strptime(x, "%Y-%m-%d") for x in ret_sorted]
    # the default is to return the original string

    if output_type == "list":
        return ret_date_formatted
    elif output_type == "pandas":
        return pd.DataFrame(ret_date_formatted, columns=["reporting_period"])
    else:
        # for now, default is to return a list
        return ret_date_formatted

    pass


def _client_factory(
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
    creds: credentials.WebserviceCredentials,
) -> Client:
    """Creates a zeep client session

    Determines whether the session argument is an FFIECConnection instance or a requests.Session instance.

    Args:
        session (_type_): _description_
        creds (_type_): _description_

    Returns:
        Client: _description_
    """
    # we have a session and valid credentials, so try to log in
    if isinstance(session, ffiec_connection.FFIECConnection):
        return _return_client_session(session.session, creds)
    elif isinstance(session, requests.Session):
        return _return_client_session(session, creds)
    else:
        raise Exception(
            "Invalid session. Must be a FFIECConnection or requests.Session instance"
        )


def collect_data(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    reporting_period: Union[str, datetime],
    rssd_id: str,
    series: str,
    output_type: str = "list",
    date_output_format: str = "string_original",
    force_null_types: Optional[str] = None,
) -> Any:
    """Return time series data from the FFIEC webservice for a given reporting period and RSSD ID

    **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
    For better performance, use OAuth2Credentials for REST API access.

    Translates the input reporting period to a FFIEC-formatted date
    Transforms the output to a pandas dataframe if output_type is 'pandas', otherwise returns a list

    | `Valid arguments for the ``reporting_period`` argument:

    * ``mm/dd/yyyy``
    * ``yyyy-mm-dd``
    * ``yyyymmdd``
    *  a python ``datetime`` object
    * For the above types, the date msut be the last day in the quarter (e.g. March 31, June 30, September 30, or December 31)
    * ``#Qyyyy``, where ``#`` is the quarter number and ``yyyy`` is the year.

    Args:
        session: The session object (can be None for REST API)
        creds: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
        reporting_period (str or datetime): Reporting period.
        rssd_id (str): The RSSD ID of the entity for which you want to retrieve data.
        series (str): `call` or `ubpr`
        output_type (str): `list`, `pandas`, or `polars`
        date_output_format (str): `string_original`, `string_yyyymmdd`, or `python_format`
        force_null_types (str, optional): Override null value handling. Options:
            - None (default): Automatic based on API (SOAP uses numpy, REST uses pandas)
            - "numpy": Force np.nan for null values (original behavior)
            - "pandas": Force pd.NA for null values (better integer handling)

    Returns:
        list, pandas DataFrame, or polars DataFrame: Returns data in the specified format

    """
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)

    # Validate force_null_types parameter
    if force_null_types is not None and force_null_types not in ["numpy", "pandas"]:
        raise_exception(
            ValidationError,
            f"Invalid force_null_types: {force_null_types}",
            field="force_null_types",
            value=force_null_types,
            expected="None, 'numpy', or 'pandas'",
        )

    # Check if we have OAuth2 credentials - attempt REST API
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        from .protocol_adapter import create_protocol_adapter

        try:
            # Cast session type for protocol adapter compatibility
            from typing import TYPE_CHECKING, cast

            if TYPE_CHECKING:
                import httpx
            adapter = create_protocol_adapter(
                creds, cast(Union["requests.Session", "httpx.Client", None], session)
            )

            # Attempt to retrieve data via REST API
            logger.debug(f"Attempting to retrieve data via REST API for RSSD {rssd_id}")
            # Convert reporting_period to string format for API
            reporting_period_str = _convert_any_date_to_ffiec_format(
                reporting_period
            ) or str(reporting_period)
            raw_data = adapter.retrieve_facsimile(rssd_id, reporting_period_str, series)

            # Process the raw data (assuming it's XBRL format)
            if isinstance(raw_data, bytes):
                ret_bytes = raw_data
            elif isinstance(raw_data, str):
                ret_bytes = raw_data.encode("utf-8")
            else:
                raise_exception(
                    ValidationError,
                    f"Invalid data type returned from REST API: {type(raw_data)}",
                    field="rest_response",
                    value=str(type(raw_data)),
                    expected="bytes or str",
                )

            # Process the XBRL data with appropriate null handling
            # Determine whether to use REST nulls based on force_null_types
            if force_null_types == "numpy":
                use_rest_nulls = False  # Force numpy nulls
            elif force_null_types == "pandas":
                use_rest_nulls = True  # Force pandas nulls
            else:
                use_rest_nulls = True  # Default for REST is pandas nulls

            processed_ret = xbrl_processor._process_xml(
                ret_bytes, date_output_format, use_rest_nulls
            )

            # Apply data normalization for consistency
            from .data_normalizer import DataNormalizer

            normalized_data = DataNormalizer.normalize_response(
                processed_ret, "RetrieveFacsimile", "REST"
            )

            # Return in requested format
            if output_type == "list":
                return normalized_data
            elif output_type == "pandas":
                df = pd.DataFrame(normalized_data)
                return df
            elif output_type == "polars":
                if not POLARS_AVAILABLE:
                    raise_exception(
                        ValidationError,
                        "Polars not available",
                        field="output_type",
                        value="polars",
                        expected="polars package must be installed: pip install polars",
                    )
                # Convert to proper Polars format with schema (same as direct XBRL path)
                if not normalized_data:
                    schema = {
                        "mdrm": pl.Utf8,
                        "rssd": pl.Utf8,
                        "id_rssd": pl.Utf8,  # Dual field support
                        "quarter": pl.Utf8,
                        "data_type": pl.Utf8,
                        "int_data": pl.Int64,
                        "float_data": pl.Float64,
                        "bool_data": pl.Boolean,
                        "str_data": pl.Utf8,
                    }
                    return pl.DataFrame([], schema=schema)

                # Convert numpy types to native Python types for polars compatibility
                polars_data = []
                for row in normalized_data:
                    polars_row = {
                        "mdrm": row["mdrm"],
                        "rssd": row["rssd"],
                        "id_rssd": row.get(
                            "id_rssd", row["rssd"]
                        ),  # Dual field support with fallback
                        "quarter": row["quarter"],
                        "data_type": row["data_type"],
                        "int_data": (
                            None if pd.isna(row["int_data"]) else int(row["int_data"])
                        ),
                        "float_data": (
                            None
                            if pd.isna(row["float_data"])
                            else float(row["float_data"])
                        ),
                        "bool_data": (
                            None
                            if pd.isna(row["bool_data"])
                            else bool(row["bool_data"])
                        ),
                        "str_data": row["str_data"],
                    }
                    polars_data.append(polars_row)

                # Create DataFrame with explicit schema to ensure correct types
                schema = {
                    "mdrm": pl.Utf8,
                    "rssd": pl.Utf8,
                    "id_rssd": pl.Utf8,  # Dual field support
                    "quarter": pl.Utf8,
                    "data_type": pl.Utf8,
                    "int_data": pl.Int64,
                    "float_data": pl.Float64,
                    "bool_data": pl.Boolean,
                    "str_data": pl.Utf8,
                }
                return pl.DataFrame(polars_data, schema=schema)

            return normalized_data

        except ConnectionError as e:
            # If REST API fails with server error, log and provide helpful message
            if "server error" in str(e).lower() or "500" in str(e):
                logger.warning(
                    f"REST API RetrieveFacsimile endpoint returned server error for RSSD {rssd_id}. "
                    f"This endpoint may not be implemented yet. "
                    f"Consider using WebserviceCredentials with SOAP API for data collection."
                )
                raise_exception(
                    ConnectionError,
                    "REST API data collection not available",
                    f"The FFIEC REST API RetrieveFacsimile endpoint returned a server error. "
                    f"This endpoint may not be implemented yet. For collecting data for RSSD {rssd_id}, "
                    f"please use WebserviceCredentials with the SOAP API. "
                    f"REST API currently supports: collect_reporting_periods, collect_filers_* functions.",
                    credential_source="oauth2_rest_api",
                )
            else:
                # Re-raise other errors
                raise

    # Original SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    # Session should not be None after validation for SOAP
    assert session is not None, "Session should not be None after validation for SOAP"
    # This SOAP path is only for WebserviceCredentials after OAuth2 routing
    assert isinstance(
        creds, credentials.WebserviceCredentials
    ), "SOAP path requires WebserviceCredentials"
    client = _client_factory(session, creds)

    reporting_period_ffiec = _return_ffiec_reporting_date(reporting_period)

    # Validate and convert RSSD ID with descriptive error
    rssd_id_int = _validate_rssd_id(rssd_id)

    # scope ret outside the if statement
    ret = None

    if series == "call":
        ret = client.service.RetrieveFacsimile(
            dataSeries="Call",
            fiIDType="ID_RSSD",
            fiID=rssd_id_int,
            reportingPeriodEndDate=reporting_period_ffiec,
            facsimileFormat="XBRL",
        )
    elif series == "ubpr":
        ret = client.service.RetrieveUBPRXBRLFacsimile(
            fiIDType="ID_RSSD",
            fiID=rssd_id_int,
            reportingPeriodEndDate=reporting_period_ffiec,
        )
    else:
        raise_exception(
            ValidationError,
            f"Invalid series: {series}",
            field="series",
            value=series,
            expected="'call' or 'ubpr'",
        )

    # Check if we received data from the webservice
    if ret is None:
        raise_exception(
            NoDataError,
            "No data returned from FFIEC webservice",
            reporting_period=str(reporting_period),
            rssd_id=rssd_id,
        )

    # Ensure ret is bytes for XML processing
    if isinstance(ret, str):
        ret_bytes = ret.encode("utf-8")
    elif isinstance(ret, bytes):
        ret_bytes = ret
    else:
        raise_exception(
            ValidationError,
            f"Invalid data type returned from webservice: {type(ret)}",
            field="webservice_response",
            value=str(type(ret)),
            expected="bytes or str",
        )

    # Process with appropriate null handling for SOAP
    # Determine whether to use REST nulls based on force_null_types
    if force_null_types == "numpy":
        use_rest_nulls = False  # Force numpy nulls
    elif force_null_types == "pandas":
        use_rest_nulls = True  # Force pandas nulls
    else:
        use_rest_nulls = False  # Default for SOAP is numpy nulls

    processed_ret = xbrl_processor._process_xml(
        ret_bytes, date_output_format, use_rest_nulls
    )

    if output_type == "list":
        return processed_ret
    elif output_type == "pandas":
        # Create DataFrame with appropriate null handling
        df = pd.DataFrame(processed_ret)

        # If we're using pd.NA (either forced or REST default), need special handling
        if use_rest_nulls:
            # Convert pd.NA to appropriate null values for pandas dtypes
            if "int_data" in df.columns:
                df["int_data"] = df["int_data"].replace({pd.NA: None}).astype("Int64")
            if "float_data" in df.columns:
                df["float_data"] = (
                    df["float_data"].replace({pd.NA: np.nan}).astype("float64")
                )
            if "bool_data" in df.columns:
                df["bool_data"] = (
                    df["bool_data"].replace({pd.NA: None}).astype("boolean")
                )
        else:
            # Traditional SOAP path with np.nan - direct conversion
            if "int_data" in df.columns:
                df["int_data"] = df["int_data"].astype("Int64")  # Nullable integer
            if "float_data" in df.columns:
                df["float_data"] = df["float_data"].astype(
                    "float64"
                )  # Regular float (supports NaN)
            if "bool_data" in df.columns:
                df["bool_data"] = df["bool_data"].astype("boolean")  # Nullable boolean

        if "str_data" in df.columns:
            df["str_data"] = df["str_data"].astype("string")  # Pandas string dtype
        return df
    elif output_type == "polars":
        if not POLARS_AVAILABLE:
            raise_exception(
                ValidationError,
                "Polars not available",
                field="output_type",
                value="polars",
                expected="polars package must be installed: pip install polars",
            )

        # Create polars DataFrame directly from processed XBRL data
        # This preserves maximum precision by avoiding pandas conversion
        if not processed_ret:
            # Return empty DataFrame with correct schema
            schema = {
                "mdrm": pl.Utf8,
                "rssd": pl.Utf8,
                "id_rssd": pl.Utf8,  # Dual field support
                "quarter": pl.Utf8,
                "data_type": pl.Utf8,
                "int_data": pl.Int64,
                "float_data": pl.Float64,
                "bool_data": pl.Boolean,
                "str_data": pl.Utf8,
            }
            return pl.DataFrame([], schema=schema)

        # Convert numpy types to native Python types for polars compatibility
        polars_data = []
        for row in processed_ret:
            polars_row = {
                "mdrm": row["mdrm"],
                "rssd": row["rssd"],
                "id_rssd": row.get(
                    "id_rssd", row["rssd"]
                ),  # Dual field support with fallback
                "quarter": row["quarter"],
                "data_type": row["data_type"],
                "int_data": None if pd.isna(row["int_data"]) else int(row["int_data"]),
                "float_data": (
                    None if pd.isna(row["float_data"]) else float(row["float_data"])
                ),
                "bool_data": (
                    None if pd.isna(row["bool_data"]) else bool(row["bool_data"])
                ),
                "str_data": row["str_data"],
            }
            polars_data.append(polars_row)

        # Create DataFrame with explicit schema to ensure correct types
        schema = {
            "mdrm": pl.Utf8,
            "rssd": pl.Utf8,
            "id_rssd": pl.Utf8,  # Dual field support
            "quarter": pl.Utf8,
            "data_type": pl.Utf8,
            "int_data": pl.Int64,
            "float_data": pl.Float64,
            "bool_data": pl.Boolean,
            "str_data": pl.Utf8,
        }

        return pl.DataFrame(polars_data, schema=schema)

    return processed_ret


def collect_filers_since_date(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    reporting_period: Union[str, datetime],
    since_date: Union[str, datetime],
    output_type: str = "list",
) -> Union[List[Any], pd.Series]:
    """Retrieves data from FFIEC webservice.

        **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
        For better performance, use OAuth2Credentials for REST API access.

    Retrieves the ID RSSDs of the reporters who have filed after a given date for a given reporting period. Note that this function only reports on Call Report filings, not UBPR filings.

        | `Valid arguments for the ``since_date`` argument:

        * ``mm/dd/yyyy``
        * ``yyyy-mm-dd``
        * ``yyyymmdd``
        *  a python ``datetime`` object

        | `Valid arguments for the ``reporting_period`` argument:

        * all of the above, as long as the date is the last day in the quarter (e.g. March 31, June 30, September 30, or December 31)
        * ``#Qyyyy``, where ``#`` is the quarter number and ``yyyy`` is the year.

        Args:
            session (FFIECConnection or requests.Session): The requests session object to use for the request.
            creds (WebserviceCredentials): The credentials to use for the request.
            since_date (str or datetime): The date to use for the request. May be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object.
            output_type (str, optional): "list" or "pandas". Defaults to "list".

        Returns:
            any: Returns either a list of dicts or a pandas Series comprising the ID RSSDs of the reporters who have filed after a given date for a given reporting period.

    """

    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _credentials_validator(creds)

    # Check if we have OAuth2 credentials - use enhanced method
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        from .methods_enhanced import collect_filers_since_date_enhanced

        return collect_filers_since_date_enhanced(
            session, creds, reporting_period, since_date, output_type
        )

    # Original SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise (
            ValueError(
                "Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."
            )
        )

    # Session should not be None after validation for SOAP
    assert session is not None, "Session should not be None after validation for SOAP"
    client = _client_factory(session, creds)

    # convert our input dates to the ffiec input date format
    since_date_ffiec = _convert_any_date_to_ffiec_format(since_date)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)

    ret = client.service.RetrieveFilersSinceDate(
        dataSeries="Call",
        lastUpdateDateTime=since_date_ffiec,
        reportingPeriodEndDate=reporting_period_datetime_ffiec,
    )

    if output_type == "list":
        return ret
    elif output_type == "pandas":
        # Provide dual column names for compatibility
        df = pd.DataFrame(ret, columns=["rssd_id"])
        df["rssd"] = df["rssd_id"]  # Dual field support
        return df
    else:
        # for now, default is to return a list
        return ret


def collect_filers_submission_date_time(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    since_date: Union[str, datetime],
    reporting_period: Union[str, datetime],
    output_type: str = "list",
    date_output_format: str = "string_original",
) -> Union[List[Any], pd.DataFrame]:
    """Retrieves data from FFIEC webservice.

        **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
        For better performance, use OAuth2Credentials for REST API access.

    Retrieves the ID RSSDs and DateTime of the reporters who have filed after a given date for a given reporting period. Note that this function only reports on Call Report filings, not UBPR filings.

        | Note on `date_output_format`:

        * ``string_original`` is the default output format, and is the format that is used by the FFIEC webservice: mm/dd/yyyy
        * ``string_yyyymmdd`` is the date in yyyymmdd format
        * ``python_format`` is the date in python datetime format

        Args:
            session (ffiec_connection.FFIECConnection or requests.Session): The requests session object to use for the request.
            creds (WebserviceCredentials or requests.Session): The credentials to use for the request.
            since_date (str or datetime): The date to use for the request. May be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object.
            reporting_period (str or datetime): The reporting period to use for the request (e.g. "2020-03-21"). Note that the date must be in the format of "YYYY-MM-DD", "YYYYMMDD", "MM/DD/YYYY", #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31.
            output_type (str, optional): "list" or "pandas". Defaults to "list".
            date_output_format (str, optional): string_original or python_datetime. Defaults to "string_original".

        Returns:
            any: List of dicts or pandas DataFrame containing the following fields:
            - "rssd"/"id_rssd": Institution RSSD ID (both field names provided for compatibility)
            - "datetime": Submission date and time in Washington DC timezone

            NOTE: Property names were inconsistent in earlier code, so both 'rssd' and 'id_rssd'
            are provided with identical data to reduce need to refactor existing user code.
    """

    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)

    # Check if we have OAuth2 credentials - use enhanced method
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        from .methods_enhanced import collect_filers_submission_date_time_enhanced

        return collect_filers_submission_date_time_enhanced(
            session,
            creds,
            since_date,
            reporting_period,
            output_type,
            date_output_format,
        )

    # Original SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise (
            ValueError(
                "Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."
            )
        )

    # we have a session and valid credentials, so try to log in
    # convert our input dates to the ffiec input date format
    since_date_ffiec = _convert_any_date_to_ffiec_format(since_date)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)

    # send the request
    # first, create the client
    assert session is not None, "Session should not be None after validation for SOAP"
    client = _client_factory(session, creds)

    ret = client.service.RetrieveFilersSubmissionDateTime(
        dataSeries="Call",
        lastUpdateDateTime=since_date_ffiec,
        reportingPeriodEndDate=reporting_period_datetime_ffiec,
    )

    # normalize the output - provide both field names for compatibility
    # NOTE: Property names were inconsistent in earlier code, so we provide both
    # 'rssd' and 'id_rssd' to reduce need to refactor existing user code
    normalized_ret = [
        {
            "rssd": str(x["ID_RSSD"]),  # Institution RSSD ID
            "id_rssd": str(x["ID_RSSD"]),  # Institution RSSD ID (same data)
            "datetime": x["DateTime"],
        }
        for x in ret
    ]

    # all submission times are in eastern time, so if we are converting to a python datetime,
    # the datetime object needs to be timezone aware, so that the user may convert the time to their local timezone
    origin_tz = ZoneInfo("US/Eastern")

    if date_output_format == "python_format":
        normalized_ret = [
            {
                "rssd": x["rssd"],
                "id_rssd": x["id_rssd"],  # Keep both field names
                "datetime": datetime.strptime(
                    x["datetime"], "%m/%d/%Y %H:%M:%S %p"
                ).replace(tzinfo=origin_tz),
            }
            for x in normalized_ret
        ]

    # convert the datetime to a string, if user requests

    if output_type == "list":
        return normalized_ret
    elif output_type == "pandas":
        return pd.DataFrame(normalized_ret)
    else:
        # for now, default is to return a list
        return ret

    pass


def collect_filers_on_reporting_period(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    reporting_period: Union[str, datetime],
    output_type: str = "list",
) -> Union[List[Any], pd.DataFrame]:
    """Retrieves data from FFIEC webservice.

    **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
    For better performance, use OAuth2Credentials for REST API access.

    Retrieves the Financial Institutions in a Panel of Reporters for a given reporting period. Note that this function only reports on Call Report filings, not UBPR filings.

    | `Valid arguments for the ``reporting_period`` argument:

    * ``mm/dd/yyyy``
    * ``yyyy-mm-dd``
    * ``yyyymmdd``
    *  a python ``datetime`` object
    * For the above types, the date must be the last day in the quarter (e.g. March 31, June 30, September 30, or December 31)
    * ``#Qyyyy``, where ``#`` is the quarter number and ``yyyy`` is the year.

    Args:
        session: The session object (can be None for REST API)
        creds: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
        reporting_period (str or datetime): The reporting period to use for the request.
    Returns:
        list or pd.DataFrame: List of dicts or pandas DataFrame containing the following fields:
        - "rssd"/"id_rssd": Institution RSSD ID (both field names provided for compatibility)
        - "fdic_cert_number": FDIC certificate number
        - "occ_chart_number": OCC charter number
        - "ots_dock_number": OTS docket number
        - "primary_aba_rout_number": Primary ABA routing number
        - "name": Institution name
        - "state": State
        - "city": City
        - "address": Street address
        - "filing_type": Filing type
        - "has_filed_for_reporting_period": Whether institution has filed for the period

        NOTE: Property names were inconsistent in earlier code, so both 'rssd' and 'id_rssd'
        are provided with identical data to reduce need to refactor existing user code.
    """

    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _credentials_validator(creds)

    # Check if we have OAuth2 credentials - use enhanced method
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        from .methods_enhanced import collect_filers_on_reporting_period_enhanced

        return collect_filers_on_reporting_period_enhanced(
            session, creds, reporting_period, output_type
        )

    # Original SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise (
            ValueError(
                "Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."
            )
        )

    assert session is not None, "Session should not be None after validation for SOAP"
    client = _client_factory(session, creds)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)

    ret = client.service.RetrievePanelOfReporters(
        dataSeries="Call", reportingPeriodEndDate=reporting_period_datetime_ffiec
    )

    normalized_ret = [datahelpers._normalize_output_from_reporter_panel(x) for x in ret]

    if output_type == "list":
        return normalized_ret
    elif output_type == "pandas":
        return pd.DataFrame(normalized_ret)
    else:
        # for now, default is to return a list
        return ret


def collect_ubpr_reporting_periods(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    output_type: str = "list",
    date_output_format: str = "string_original",
) -> Union[List[Any], pd.DataFrame]:
    """Retrieves UBPR reporting periods from FFIEC API.

    **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
    For better performance, use OAuth2Credentials for REST API access.

    Args:
        session: The session object (can be None for REST API)
        creds: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
        output_type: Output format ("list", "pandas", or "polars")
        date_output_format: Date format for output

    Returns:
        list or pd.DataFrame: List of UBPR reporting periods in ascending chronological order (oldest first)
    """

    # Validate inputs
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)

    # Check if we have OAuth2 credentials - use REST API
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        try:
            from .protocol_adapter import create_protocol_adapter

            adapter = create_protocol_adapter(creds, session)  # type: ignore[arg-type]
            raw_periods = adapter.retrieve_ubpr_reporting_periods()

            # Sort reporting periods in ascending chronological order (oldest first)
            sorted_periods = sort_reporting_periods_ascending(raw_periods)

            # Handle output type conversion
            if output_type == "pandas":
                return pd.DataFrame({"reporting_period": sorted_periods})
            else:
                return sorted_periods

        except Exception as e:
            logger.error(f"REST API call failed for UBPR reporting periods: {e}")
            raise_exception(
                ConnectionError,
                f"Failed to retrieve UBPR reporting periods via REST API: {e}",
            )

    # SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    # For SOAP API, UBPR periods would need to be implemented
    # Currently not available in SOAP API per the documentation
    raise_exception(
        ValidationError,
        "UBPR reporting periods are only available via REST API. Please use OAuth2Credentials.",
        field="credentials",
        value="WebserviceCredentials",
        expected="OAuth2Credentials for UBPR access",
    )


def collect_ubpr_facsimile_data(
    session: Union[ffiec_connection.FFIECConnection, requests.Session, None],
    creds: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
    reporting_period: Union[str, datetime],
    rssd_id: str,
    output_type: str = "list",
    force_null_types: Optional[str] = None,
) -> Union[bytes, List[Any], pd.DataFrame]:
    """Retrieves UBPR XBRL facsimile data for a specific institution.

    **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
    For better performance, use OAuth2Credentials for REST API access.

    Args:
        session: The session object (can be None for REST API)
        creds: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
        reporting_period: Reporting period date
        rssd_id: Institution RSSD ID
        output_type: Output format ("list", "pandas", "polars", or "bytes")
        force_null_types (str, optional): Override null value handling. Options:
            - None (default): Automatic based on API (REST uses pandas)
            - "numpy": Force np.nan for null values
            - "pandas": Force pd.NA for null values

    Returns:
        bytes, list, or pd.DataFrame: UBPR XBRL data
    """

    # Validate inputs
    _ = _output_type_validator(output_type)
    _ = _credentials_validator(creds)

    # Validate force_null_types parameter
    if force_null_types is not None and force_null_types not in ["numpy", "pandas"]:
        raise_exception(
            ValidationError,
            f"Invalid force_null_types: {force_null_types}",
            field="force_null_types",
            value=force_null_types,
            expected="None, 'numpy', or 'pandas'",
        )

    # Validate reporting period
    if not _is_valid_date_or_quarter(reporting_period):
        raise_exception(
            ValidationError,
            "Invalid reporting period format",
            field="reporting_period",
            value=str(reporting_period),
            expected="MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD, #QYYYY or datetime object",
        )

    # Check if we have OAuth2 credentials - use REST API
    from .credentials import OAuth2Credentials

    if isinstance(creds, OAuth2Credentials):
        try:
            from .protocol_adapter import create_protocol_adapter

            # Convert reporting period to FFIEC format
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
                    )

            assert ffiec_date is not None  # Helps mypy understand control flow
            adapter = create_protocol_adapter(creds, session)  # type: ignore[arg-type]
            raw_data = adapter.retrieve_ubpr_xbrl_facsimile(rssd_id, ffiec_date)

            # Handle output type
            if output_type == "bytes":
                return raw_data

            # Process XBRL data if needed
            if isinstance(raw_data, bytes):
                # Determine null handling
                if force_null_types == "numpy":
                    use_rest_nulls = False
                elif force_null_types == "pandas":
                    use_rest_nulls = True
                else:
                    use_rest_nulls = True  # Default for REST is pandas nulls

                if output_type == "list":
                    # Parse XBRL and return as list
                    processed_data = xbrl_processor._process_xml(
                        raw_data, "string_original", use_rest_nulls
                    )
                    return processed_data
                elif output_type == "pandas":
                    processed_data = xbrl_processor._process_xml(
                        raw_data, "string_original", use_rest_nulls
                    )
                    df = pd.DataFrame(processed_data)

                    # Handle null types based on what we're using
                    if use_rest_nulls:
                        # Convert pd.NA to appropriate null values for pandas dtypes
                        if "int_data" in df.columns:
                            df["int_data"] = (
                                df["int_data"].replace({pd.NA: None}).astype("Int64")
                            )
                        if "float_data" in df.columns:
                            df["float_data"] = (
                                df["float_data"]
                                .replace({pd.NA: np.nan})
                                .astype("float64")
                            )
                        if "bool_data" in df.columns:
                            df["bool_data"] = (
                                df["bool_data"].replace({pd.NA: None}).astype("boolean")
                            )
                    else:
                        # Traditional np.nan path - direct conversion
                        if "int_data" in df.columns:
                            df["int_data"] = df["int_data"].astype("Int64")
                        if "float_data" in df.columns:
                            df["float_data"] = df["float_data"].astype("float64")
                        if "bool_data" in df.columns:
                            df["bool_data"] = df["bool_data"].astype("boolean")

                    if "str_data" in df.columns:
                        df["str_data"] = df["str_data"].astype("string")

                    return df
                else:
                    return raw_data
            else:
                return raw_data

        except Exception as e:
            logger.error(f"REST API call failed for UBPR facsimile data: {e}")
            raise_exception(
                ConnectionError,
                f"Failed to retrieve UBPR facsimile data via REST API: {e}",
            )

    # SOAP implementation for WebserviceCredentials
    _ = _session_validator(session)

    # For SOAP API, UBPR facsimile would need to be implemented
    # Currently not available in SOAP API per the documentation
    raise_exception(
        ValidationError,
        "UBPR facsimile data is only available via REST API. Please use OAuth2Credentials.",
        field="credentials",
        value="WebserviceCredentials",
        expected="OAuth2Credentials for UBPR access",
    )
