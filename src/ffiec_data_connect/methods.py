"""Methods that wrap the FFIEC Webservice API

The methods contained in this module are utilized to call and collect data from the FFIEC Webservice API.

"""

import re
from typing import Optional, Union

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
from datetime import datetime
from zoneinfo import ZoneInfo

from zeep import Client

from ffiec_data_connect import (
    credentials,
    datahelpers,
    ffiec_connection,
    xbrl_processor,
)
from ffiec_data_connect.exceptions import (
    NoDataError,
    ValidationError,
    raise_exception,
)

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
    valid_types = ["list", "pandas", "polars"]
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


def _credentials_validator(creds: credentials.WebserviceCredentials) -> bool:
    """Internal function to validate the credentials

    Args:
        creds (credentials.WebserviceCredentials): the credentials to validate

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If credentials are invalid
    """
    if not isinstance(creds, credentials.WebserviceCredentials):
        raise_exception(
            ValidationError,
            "Invalid credentials type",
            field="credentials",
            value=type(creds).__name__,
            expected="WebserviceCredentials instance",
        )
    return True


def _session_validator(
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
) -> bool:
    """Internal function to validate the session

    Args:
        session (requests.Session): the session to validate

    Returns:
        bool: True if valid

    Raises:
        ValidationError: If session is invalid
    """
    if isinstance(session, ffiec_connection.FFIECConnection):
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
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
    creds: credentials.WebserviceCredentials,
    series="call",
    output_type="list",
    date_output_format="string_original",
) -> Union[list, pd.Series]:
    """Returns list of reporting periods available for access via the FFIEC webservice

    | Note on `date_output_format`:

    * ``string_original`` is the default output format, and is the format that is used by the FFIEC webservice: mm/dd/yyyy
    * ``string_yyyymmdd`` is the date in yyyymmdd format
    * ``python_format`` is the date in python datetime format


    Args:
        session (requests.Session): The requests session object to use for the request.
        creds (credentials.WebserviceCredentials): The credentials to use for the request.
        series (str, optional): `call` or `ubpr`
        output_type (str): `list` or `pandas`
        date_output_format: `string_original`, `string_yyyymmdd`, or `python_format`

    Returns:
        `list` or `Pandas` series: Returns a list of reporting periods from the FFIEC Webservice

    """

    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)

    # we have a session and valid credentials, so try to log in
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
    ret_date_formatted = ret

    if date_output_format == "string_yyyymmdd":
        ret_date_formatted = [
            datetime.strftime(datetime.strptime(x, "%Y-%m-%d"), "%Y%m%d") for x in ret
        ]
    elif date_output_format == "python_format":
        ret_date_formatted = [datetime.strptime(x, "%Y-%m-%d") for x in ret]
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
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
    creds: credentials.WebserviceCredentials,
    reporting_period: Union[str, datetime],
    rssd_id: str,
    series: str,
    output_type="list",
    date_output_format="string_original",
):
    """Return time series data from the FFIEC webservice for a given reporting period and RSSD ID

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
        session (FFIECConnection or requests.Session): The requests session object to use for the request.
        creds (WebserviceCredentials): The credentials to use for the request.
        reporting_period (str or datetime): Reporting period.
        rssd_id (str): The RSSD ID of the entity for which you want to retrieve data.
        series (str): `call` or `ubpr`
        output_type (str): `list`, `pandas`, or `polars`
        date_output_format (str): `string_original`, `string_yyyymmdd`, or `python_format`

    Returns:
        list, pandas DataFrame, or polars DataFrame: Returns data in the specified format

    """
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)

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

    processed_ret = xbrl_processor._process_xml(ret_bytes, date_output_format)

    if output_type == "list":
        return processed_ret
    elif output_type == "pandas":
        df = pd.DataFrame(processed_ret)
        # Ensure proper dtypes with nullable support for pandas DataFrame
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
                "quarter": row["quarter"],
                "data_type": row["data_type"],
                "int_data": None if np.isnan(row["int_data"]) else int(row["int_data"]),
                "float_data": (
                    None if np.isnan(row["float_data"]) else float(row["float_data"])
                ),
                "bool_data": (
                    None if np.isnan(row["bool_data"]) else bool(row["bool_data"])
                ),
                "str_data": row["str_data"],
            }
            polars_data.append(polars_row)

        # Create DataFrame with explicit schema to ensure correct types
        schema = {
            "mdrm": pl.Utf8,
            "rssd": pl.Utf8,
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
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
    creds: credentials.WebserviceCredentials,
    reporting_period: Union[str, datetime],
    since_date: Union[str, datetime],
    output_type="list",
) -> Union[list, pd.Series]:
    """Retrieves the ID RSSDs of the reporters who have filed after a given date for a given reporting period. Note that this function only reports on Call Report filings, not UBPR filings.

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
    _ = _session_validator(session)

    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise (
            ValueError(
                "Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."
            )
        )

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
        return pd.DataFrame(ret, columns=["rssd_id"])
    else:
        # for now, default is to return a list
        return ret


def collect_filers_submission_date_time(
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
    creds: credentials.WebserviceCredentials,
    since_date: Union[str, datetime],
    reporting_period: Union[str, datetime],
    output_type: str = "list",
    date_output_format: str = "string_original",
) -> Union[list, pd.DataFrame]:
    """Retrieves the ID RSSDs and DateTime of the reporters who have filed after a given date for a given reporting period. Note that this function only reports on Call Report filings, not UBPR filings.

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
        any: List of dicts or pandas DataFrame containing the rssd id of the filer, and the submission date and time, in Washington DC timezone.
    """

    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)

    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise (
            ValueError(
                "Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."
            )
        )

    # we have a session and valid credentials, so try to log in
    client = _client_factory(session, creds)

    # convert our input dates to the ffiec input date format
    since_date_ffiec = _convert_any_date_to_ffiec_format(since_date)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)

    # send the request

    # first, create the client
    client = _client_factory(session, creds)

    ret = client.service.RetrieveFilersSubmissionDateTime(
        dataSeries="Call",
        lastUpdateDateTime=since_date_ffiec,
        reportingPeriodEndDate=reporting_period_datetime_ffiec,
    )

    # normalize the output
    normalized_ret = [{"rssd": x["ID_RSSD"], "datetime": x["DateTime"]} for x in ret]

    # all submission times are in eastern time, so if we are converting to a python datetime,
    # the datetime object needs to be timezone aware, so that the user may convert the time to their local timezone
    origin_tz = ZoneInfo("US/Eastern")

    if date_output_format == "python_format":
        normalized_ret = [
            {
                "rssd": x["rssd"],
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
    session: Union[ffiec_connection.FFIECConnection, requests.Session],
    creds: credentials.WebserviceCredentials,
    reporting_period: Union[str, datetime],
    output_type="list",
) -> Union[list, pd.DataFrame]:
    """Retrieves the Financial Institutions in a Panel of Reporters for a given reporting period. Note that this function only reports on Call Report filings, not UBPR filings.

    | `Valid arguments for the ``reporting_period`` argument:

    * ``mm/dd/yyyy``
    * ``yyyy-mm-dd``
    * ``yyyymmdd``
    *  a python ``datetime`` object
    * For the above types, the date must be the last day in the quarter (e.g. March 31, June 30, September 30, or December 31)
    * ``#Qyyyy``, where ``#`` is the quarter number and ``yyyy`` is the year.


    Args:
        session (ffiec_connection.FFIECConnection or requests.Session): The requests session object to use for the request.
        creds (credentials.WebserviceCredentials): The credentials to use for the request.
        reporting_period (str or datetime): The reporting period to use for the request.
    Returns:
        list or pd.DataFrame: List of dicts or pandas DataFrame containing the rssd id of the filer, and the following fields: "id_rssd", "fdic_cert_number", "occ_chart_number", "ots_dock_number", "primary_aba_rout_number", "name", "state", "city", "address", "filing_type", "has_filed_for_reporting_period"
    """

    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)

    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise (
            ValueError(
                "Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."
            )
        )

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
