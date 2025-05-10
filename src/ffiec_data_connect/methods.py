"""Methods that wrap the FFIEC Webservice API

The methods contained in this module are utilized to call and collect data from the FFIEC Webservice API.

"""

import re
import requests
import pandas as pd
from typing import Union
from datetime import datetime
from zoneinfo import ZoneInfo
from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport
import polars as pl
from ffiec_data_connect import datahelpers, credentials, constants, xbrl_processor, ffiec_connection
import pyarrow as pa
# global date regex
quarterStringRegex = r"^[1-4](q|Q)([0-9]{4})$"
yyyymmddRegex = r"^[0-9]{4}[0-9]{2}[0-9]{2}$"
yyyymmddDashRegex = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
mmddyyyyRegex = r"^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$"

validRegexList = [quarterStringRegex, yyyymmddRegex, yyyymmddDashRegex, mmddyyyyRegex]


def _create_ffiec_date_from_datetime(indate: datetime) -> str:
    """
    [INTERNAL USE ONLY]
    Converts a datetime object to a FFIEC-formatted date string (MM/DD/YYYY).

    Args:
        indate (datetime): The date to convert.

    Returns:
        str: The date in FFIEC format (MM/DD/YYYY).
    """
    month_str = str(indate.month)
    day_str = str(indate.day)
    year_str = str(indate.year)
    
    mmddyyyy = month_str + "/" + day_str + "/" + year_str
    
    return mmddyyyy


def _convert_any_date_to_ffiec_format(indate: Union[str, datetime]) -> str:
    """
    [INTERNAL USE ONLY]
    Converts a string-based date or python datetime object to a FFIEC-formatted date string (MM/DD/YYYY).

    Args:
        indate (str or datetime): The date to convert. Accepts string in the format of "YYYY-MM-DD", "YYYYMMDD", "MM/DD/YYYY", or a python datetime object.

    Returns:
        str: The date in FFIEC format (MM/DD/YYYY).

    Raises:
        ValueError: If the input is not a recognized date format or a datetime object.
    """
    
    if isinstance(indate, datetime):
        return _create_ffiec_date_from_datetime(indate)
    elif isinstance(indate, str):
        # does the date have two slashes?
        if indate.count("-") == 2:
            return _create_ffiec_date_from_datetime(datetime.strptime(indate, "%Y-%m-%d"))
        elif indate.count("/") == 2:
            return _create_ffiec_date_from_datetime(datetime.strptime(indate, "%m/%d/%Y"))
        elif len(indate) == 8:
            return _create_ffiec_date_from_datetime(datetime.strptime(indate, "%Y%m%d"))  
    else:
        # raise an error if we don't have a valid date
        raise(ValueError("Invalid date format. Must be a string in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object"))
    
def _convert_any_date_to_python_format(indate: Union[str, datetime]) -> datetime:
    """
    [INTERNAL USE ONLY]
    Converts a string-based date or python datetime object to a python datetime object.

    Args:
        indate (str or datetime): The date to convert. Accepts string in the format of "YYYY-MM-DD", "YYYYMMDD", "MM/DD/YYYY", or a python datetime object.

    Returns:
        datetime: The date as a Python datetime object.

    Raises:
        ValueError: If the input is not a recognized date format or a datetime object.
    """
    if isinstance(indate, datetime):
        return indate
    elif isinstance(indate, str):
        return datetime.strptime(_convert_any_date_to_ffiec_format(indate), "%m/%d/%Y")
    else:
        raise(ValueError("Invalid date format. Must be a string in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object"))

def _convert_quarter_to_date(reporting_period: str) -> datetime:
    """
    [INTERNAL USE ONLY]
    Converts a string in the format of #QYYYY to a datetime object representing the last day of the quarter.

    Args:
        reporting_period (str): Quarter string (e.g., '1Q2024').

    Returns:
        datetime: The last day of the specified quarter.

    Raises:
        ValueError: If the quarter number is invalid.
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
            raise(ValueError("Invalid quarter number")) # raise an error if we don't have a valid quarter number
    pass
    

def _is_valid_date_or_quarter(reporting_period: Union[str, datetime]) -> bool:
    """
    [INTERNAL USE ONLY]
    Validates the reporting period input argument, which should indicate either the name of a calendar quarter, a string that represents the last day of a quarter, or a datetime object.

    Args:
        reporting_period (str or datetime): The reporting period to validate.

    Returns:
        bool: True if valid reporting period, False otherwise.
    """

    if isinstance(reporting_period, datetime):
        # what is the month of the quarter?
        month = reporting_period.month # 1 = Jan, 12= Dec
        day = reporting_period.day # 1 = 1st
        
        if month in [3,12]:
            if day == 31:
                return True # the quarter ends on the 31st in March and December
            else:
                return False
        elif month in [6,9]:
            if day == 30:
                return True # the quarter ends on the 30th in June, September
            else:
                return False
    elif isinstance(reporting_period, str):
        # does our date match any of the valid regexes?
        return any(re.search(regex, reporting_period) for regex in validRegexList)
    else:
        return False # we don't know what to do with this type of input, so return false
    
    
def _return_ffiec_reporting_date(indate: Union[datetime, str]) -> str:
    """
    [INTERNAL USE ONLY]
    Converts a datetime or string to a FFIEC-formatted reporting date string (MM/DD/YYYY).

    Args:
        indate (datetime or str): The date or quarter string to convert.

    Returns:
        str: The date in FFIEC format (MM/DD/YYYY).

    Raises:
        ValueError: If the date is not a valid quarter end.
    """
    if isinstance(indate, datetime):
        return _create_ffiec_date_from_datetime(indate)
    elif isinstance(indate, str):
        if indate[1] == "Q":
            return _create_ffiec_date_from_datetime(_convert_quarter_to_date(indate))
        else:
            ffiec_date =  _convert_any_date_to_ffiec_format(indate)
            ffiec_date_month = ffiec_date.split("/")[0]
            ffiec_date_date = ffiec_date.split("/")[1]
            
            if (ffiec_date_month == "3" or ffiec_date_month == "03") and ffiec_date_date == "31":
                return ffiec_date
            elif (ffiec_date_month == "6" or ffiec_date_month == "06") and ffiec_date_date == "30":
                return ffiec_date
            elif (ffiec_date_month == "9" or ffiec_date_month == "09") and ffiec_date_date == "30":
                return ffiec_date
            elif ffiec_date_month == "12" and ffiec_date_date == "31":
                return ffiec_date
            else:
                raise(ValueError("Invalid date format. Must be a string in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', or a python datetime object"))
    
def _output_type_validator(output_type: str) -> bool:
    """
    [INTERNAL USE ONLY]
    Validates the output_type argument.

    Args:
        output_type (str): The output_type to validate ('list', 'pandas', or 'polars').

    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if output_type not in ['list', 'pandas', 'polars']:
        raise(ValueError("Invalid output_type. Must be 'list', 'pandas', or 'polars'"))
    else:
        return True
    
def _date_format_validator(date_format: str) -> bool:
    """
    [INTERNAL USE ONLY]
    Validates the date_format argument.

    Args:
        date_format (str): The date_format to validate ('string_original', 'string_yyyymmdd', or 'python_format').

    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if date_format not in ['string_original', 'string_yyyymmdd', 'python_format']:
        raise(ValueError("Invalid date_format. Must be 'string_original', 'string_yyyymmdd', or 'python_format'"))
    else:
        return True
    

def _credentials_validator(creds: credentials.WebserviceCredentials) -> bool:
    """
    [INTERNAL USE ONLY]
    Validates the credentials argument.

    Args:
        creds (credentials.WebserviceCredentials): The credentials to validate.

    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if not isinstance(creds, credentials.WebserviceCredentials):
        raise(ValueError("Invalid credentials. Must be a WebserviceCredentials instance"))
    else:
        return True
    
def _session_validator(session: requests.Session) -> bool:
    """
    [INTERNAL USE ONLY]
    Validates the session argument.

    Args:
        session (requests.Session): The session to validate.

    Returns:
        bool: True if valid, raises ValueError otherwise.
    """
    if isinstance(session, ffiec_connection.FFIECConnection):
        return True
    elif isinstance(session, requests.Session):
        return True
    else:
        raise(ValueError("Invalid session/connection. Must be a requests.Session instance or FFIECConnection instance"))
    
def _return_client_session(session: requests.Session, creds: credentials.WebserviceCredentials) -> Client:
    """
    [INTERNAL USE ONLY]
    Returns a zeep client session for the FFIEC webservice.

    Args:
        session (requests.Session): The requests.Session object to use.
        creds (credentials.WebserviceCredentials): The credentials to use.

    Returns:
        Client: Zeep SOAP client for the FFIEC webservice.
    """
    
    # create a transport
    transport = Transport(session=session)
    
    wsse = UsernameToken(creds.username, creds.password)
                         
    # create the client
    soap_client = Client(constants.WebserviceConstants.base_url, wsse=wsse, transport=transport)
    
    return soap_client




def collect_reporting_periods(session: requests.Session, creds: credentials.WebserviceCredentials, series= "call", output_type = "list", date_output_format="string_original") -> Union[list, pd.Series, pl.Series]:
    """Returns list of reporting periods available for access via the FFIEC webservice

    | Note on `date_output_format`:
    
    * ``string_original`` is the default output format, and is the format that is used by the FFIEC webservice: mm/dd/yyyy
    * ``string_yyyymmdd`` is the date in yyyymmdd format
    * ``python_format`` is the date in python datetime format


    Args:
        session (requests.Session): The requests session object to use for the request.
        creds (credentials.WebserviceCredentials): The credentials to use for the request.
        series (str, optional): `call` or `ubpr`
        output_type (str): `list`, `pandas`, or `polars`
        date_output_format: `string_original`, `string_yyyymmdd`, or `python_format`

    Returns:
        `list`, `Pandas Series`, or `Polars Series`: Returns a list of reporting periods from the FFIEC Webservice
        
    """
    
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)

    
    ## we have a session and valid credentials, so try to log in
    client  = _client_factory(session, creds)
    
    ## scope ret outside the if statement
    ret = None
    
    if series == "call":
        ret = client.service.RetrieveReportingPeriods(dataSeries="Call")
    elif series == "ubpr":
        ret = client.service.RetrieveUBPRReportingPeriods()
    
    
    # did we return anything? if not, raise an error
    if ret is None:
        raise ValueError("No reporting periods returned.")
    
    ret_date_formatted = ret
        
    if date_output_format == "string_yyyymmdd":
        #ret_date_formatted = [datetime.strftime(datetime.strptime(x, "%m/%d/%Y"), "%Y%m%d") for x in ret]
        ret_date_formatted = [_convert_any_date_to_ffiec_format(x) for x in ret]
    elif date_output_format == "python_format":
        ret_date_formatted =  [_convert_any_date_to_python_format(x) for x in ret]
    # the default is to return the original string
        
    if output_type == "list":
        return ret_date_formatted
    elif output_type == "pandas":
        return pd.Series(ret_date_formatted, name='reporting_period')
    elif output_type == "polars":
        return pl.Series(name='reporting_period', values=ret_date_formatted)
    else:
        # for now, default is to return a list
        return ret_date_formatted
    
    pass
    

def _client_factory(session, creds)-> Client:
    """Creates a zeep client session
    
    Determines whether the session argument is an FFIECConnection instance or a requests.Session instance.

    Args:
        session (_type_): _description_
        creds (_type_): _description_

    Returns:
        Client: _description_
    """
        ## we have a session and valid credentials, so try to log in
    if isinstance(session, ffiec_connection.FFIECConnection):
        return  _return_client_session(session.session, creds)
    elif isinstance(session, requests.Session):
        return _return_client_session(session, creds)
    else:
        raise Exception("Invalid session. Must be a FFIECConnection or requests.Session instance")
    

def collect_data(session: Union[ffiec_connection.FFIECConnection, requests.Session], creds: credentials.WebserviceCredentials, reporting_period: Union[str, datetime], rssd_id:str, series: str, output_type = "list", date_output_format ="string_original") -> Union[list, pd.DataFrame, pl.DataFrame]:
    """
    Return time series data from the FFIEC webservice for a given reporting period and RSSD ID.

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
        output_type (str): `list` or `pandas`
        date_output_format (str): `string_original`, `string_yyyymmdd`, or `python_format`

    Returns:
        list or pandas: Returns either a list of dicts or a pandas DataFrame
        
    Raises:
        ValueError: If input arguments are invalid or if no data is returned.
        Exception: For other unexpected errors.

    Example:
        >>> df = collect_data(session, creds, '2024-12-31', '12345', 'call', output_type='polars')
    """
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)
    

    client = _client_factory(session, creds)
    
    reporting_period_ffiec = _return_ffiec_reporting_date(reporting_period)
    
    #print("Reporting period: {}".format(reporting_period_ffiec))
    
    # try to convert the rssd_id to an int and raise an error if it fails
    rssd_id_int = int(rssd_id)
    
    
    ## scope ret outside the if statement
    ret = None
    
    if series == "call":
        ret = client.service.RetrieveFacsimile(dataSeries="Call", fiIDType="ID_RSSD", fiID=rssd_id_int, reportingPeriodEndDate=reporting_period_ffiec, facsimileFormat="XBRL")
    elif series == "ubpr":
        ret = client.service.RetrieveUBPRXBRLFacsimile(fiIDType="ID_RSSD", fiID=rssd_id_int, reportingPeriodEndDate=reporting_period_ffiec)
    
    processed_ret = xbrl_processor._process_xml(ret, date_output_format)
    
    if output_type == "list":
        return processed_ret
    elif output_type == "pandas":
        return pd.DataFrame(processed_ret)
    elif output_type == "polars":

        # This is the schema that we would use if we wanted to explicitly set the types of the columns,
        # using python-based date types.
        
        # polars_schema_python_time = {
        #     "mdrm": pl.String,
        #     "rssd": pl.String,
        #     "quarter": pl.Date,    # Target Polars Date type
        #     "int_data": pl.Int64,   # Polars native nullable integer.
        #     "float_data": pl.Float64,
        #     "bool_data": pl.Boolean,
        #     "str_data": pl.String,
        #     "data_type": pl.String
        # }
        
        # This is the schema we would use if we wanted to keep the original date format, which is usually MM/DD/YYYY
        # polars_schema_original_date = {
        #     "mdrm": pl.String,
        #     "rssd": pl.String,
        #     "quarter": pl.String,
        #     "int_data": pl.Int64,
        #     "float_data": pl.Float64,
        #     "bool_data": pl.Boolean,
        #     "str_data": pl.String,
        #     "data_type": pl.String
        # }

        # convert the input data to pandas, and then coerce each column to the appropriate polars type
        pandas_df = pd.DataFrame(processed_ret)
        
        # remove any rows where the rssd is null or mdrm is null
        pandas_df = pandas_df[pandas_df['rssd'].notna()]
        pandas_df = pandas_df[pandas_df['mdrm'].notna()]
        
        # Prepare Pandas DataFrame columns for Polars conversion

        # Ensure 'mdrm' and 'rssd' are string type.
        # These columns are asserted to exist due to the .notna() filters above.
        pandas_df['mdrm'] = pandas_df['mdrm'].astype(str)
        pandas_df['rssd'] = pandas_df['rssd'].astype(str)

        # Convert 'quarter' column to datetime.date objects.
        # _convert_any_date_to_python_format is assumed to return datetime.datetime.
        if 'quarter' in pandas_df.columns:
            
            # if the requested date_output_format is python_format, then we need to convert the quarter to a datetime.date object, otherwise we can just use the quarter as is
            if date_output_format == "python_format":
                pandas_df['quarter'] = pandas_df['quarter'].apply(
                    lambda x: _convert_any_date_to_python_format(x).date() if pd.notna(x) else None
                )

        # Coerce 'int_data' to numeric. Errors become NaN.
        # Polars' schema_override to pl.Int64 will handle NaNs as nulls.
        if 'int_data' in pandas_df.columns:
            pandas_df['int_data'] = pd.to_numeric(pandas_df['int_data'], errors='coerce')

        # Coerce 'float_data' to numeric. Errors become NaN.
        if 'float_data' in pandas_df.columns:
            pandas_df['float_data'] = pd.to_numeric(pandas_df['float_data'], errors='coerce')

        # Convert 'bool_data' to Pandas nullable boolean type (pd.BooleanDtype()).
        # This handles Python None/NaN correctly before Polars pl.Boolean conversion.
        if 'bool_data' in pandas_df.columns:
            pandas_df['bool_data'] = pandas_df['bool_data'].astype(pd.BooleanDtype())

        # For 'str_data' and 'data_type', if _process_xml produces Python None for missing values,
        # Pandas will keep them as None in an object-dtype column.
        # pl.from_pandas with schema_overrides to pl.String will correctly convert these Nones to Polars nulls.
        # Explicit .astype(str) here would convert None to the string "None", which is usually not desired.
        # If these columns might contain non-string/non-None data that needs to be stringified,
        # then specific handling or .astype(str) would be needed. Assuming clean input for now.

        if 'data_type' in pandas_df.columns:
            pandas_df['data_type'] = pandas_df['data_type'].astype(str) # Converts None to "None"
        if 'str_data' in pandas_df.columns:
            pandas_df['str_data'] = pandas_df['str_data'].astype(str) # Converts None to "None"


        pyarrow_table = pa.Table.from_pandas(pandas_df)

        # check that the pandas_df is not empty
        if pandas_df.empty:
            raise ValueError("Pandas DataFrame is empty. Please check the input data and try again.")

        return pl.from_arrow(pyarrow_table)    
    
    
def collect_filers_since_date(session: Union[ffiec_connection.FFIECConnection , requests.Session], creds: credentials.WebserviceCredentials, reporting_period: Union[str, datetime], since_date: Union[str, datetime], output_type = "list") -> Union[list, pd.Series, pl.Series]:
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
        output_type (str, optional): "list", "pandas", or "polars". Defaults to "list".

    Returns:
        list, Pandas Series, or Polars Series: Returns either a list of dicts, a pandas Series, or a Polars Series comprising the ID RSSDs of the reporters who have filed after a given date for a given reporting period.
        
    """
    
    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)
    
    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise(ValueError("Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."))
    
    
    client = _client_factory(session, creds)
    
    # convert our input dates to the ffiec input date format
    since_date_ffiec = _convert_any_date_to_ffiec_format(since_date)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)
    

    
    ret = client.service.RetrieveFilersSinceDate(dataSeries="Call",  lastUpdateDateTime=since_date_ffiec, reportingPeriodEndDate=reporting_period_datetime_ffiec)
    
    
    if output_type == "list":
        return ret
    elif output_type == "pandas":
        return pd.Series(ret, name='rssd_id')
    elif output_type == "polars":
        return pl.Series(name='rssd_id', values=ret)
    else:
        # for now, default is to return a list
        return ret
    
    

def collect_filers_submission_date_time(session: Union[ffiec_connection.FFIECConnection, requests.Session], creds: credentials.WebserviceCredentials, since_date: Union[str, datetime], reporting_period: Union[str, datetime], output_type = "list", date_output_format ="string_original") -> Union[list, pd.DataFrame, pl.DataFrame]:
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
        output_type (str, optional): "list", "pandas", or "polars". Defaults to "list".
        date_output_format (str, optional): string_original or python_datetime. Defaults to "string_original".

    Returns:
        list, Pandas DataFrame, or Polars DataFrame: List of dicts, pandas DataFrame, or Polars DataFrame containing the rssd id of the filer, and the submission date and time, in Washington DC timezone.
    """
    
        
    # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _date_format_validator(date_output_format)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)
    
    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise(ValueError("Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."))
    
    
    ## we have a session and valid credentials, so try to log in
    client = _client_factory(session, creds)
    
    # convert our input dates to the ffiec input date format
    since_date_ffiec = _convert_any_date_to_ffiec_format(since_date)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)
    
    # send the request
    
    # first, create the client
    client = _client_factory(session, creds)
    
    ret = client.service.RetrieveFilersSubmissionDateTime(dataSeries="Call", lastUpdateDateTime=since_date_ffiec, reportingPeriodEndDate=reporting_period_datetime_ffiec)
    
    # normalize the output
    normalized_ret = [{"rssd":x["ID_RSSD"], "datetime":x["DateTime"]} for x in ret]
    

    # all submission times are in eastern time, so if we are converting to a python datetime,
    # the datetime object needs to be timezone aware, so that the user may convert the time to their local timezone    
    origin_tz = ZoneInfo("US/Eastern")

    
    if date_output_format == "python_format":
        normalized_ret = [{"rssd":x["rssd"], "datetime":datetime.strptime(x["datetime"], "%m/%d/%Y %H:%M:%S %p").replace(tzinfo=origin_tz)} for x in normalized_ret]
    

    # convert the datetime to a string, if user requests
    
    if output_type == "list":
        return normalized_ret
    elif output_type == "pandas":
        return pd.DataFrame(normalized_ret)
    elif output_type == "polars":
        return pl.DataFrame(normalized_ret, schema=['rssd_id', 'datetime'])
    else:
        # for now, default is to return a list
        return ret
    
    
    pass

def collect_filers_on_reporting_period(session: Union[ffiec_connection.FFIECConnection, requests.Session], creds: credentials.WebserviceCredentials, reporting_period: Union[str, datetime], output_type = "list") -> Union[list, pd.DataFrame, pl.DataFrame]:
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
        output_type (str, optional): "list", "pandas", or "polars". Defaults to "list".
    Returns:
        list, pd.DataFrame, or pl.DataFrame: List of dicts, pandas DataFrame, or Polars DataFrame containing the rssd id of the filer, and the following fields: "id_rssd", "fdic_cert_number", "occ_chart_number", "ots_dock_number", "primary_aba_rout_number", "name", "state", "city", "address", "filing_type", "has_filed_for_reporting_period"
    """
    
        # conduct standard validation on function input arguments
    _ = _output_type_validator(output_type)
    _ = _credentials_validator(creds)
    _ = _session_validator(session)
    
    is_valid_reporting_period = _is_valid_date_or_quarter(reporting_period)
    if not is_valid_reporting_period:
        raise(ValueError("Reporting period must be in the format of 'YYYY-MM-DD', 'YYYYMMDD', 'MM/DD/YYYY', #QYYYY or a python datetime object, with the month and date set to March 31, June 30, September 30, or December 31."))
    
    
    client = _client_factory(session, creds)
    reporting_period_datetime_ffiec = _return_ffiec_reporting_date(reporting_period)
    
    ret = client.service.RetrievePanelOfReporters(dataSeries="Call", reportingPeriodEndDate=reporting_period_datetime_ffiec)
    
    normalized_ret = [datahelpers._normalize_output_from_reporter_panel(x) for x in ret]
    
    if output_type == "list":
        return normalized_ret
    elif output_type == "pandas":
        return pd.DataFrame(normalized_ret)
    elif output_type == "polars":
        return pl.DataFrame(normalized_ret)
    else:
        # for now, default is to return a list
        return ret
    
