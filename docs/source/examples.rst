Example Code
============

This page provides practical examples for using the `ffiec_data_connect` package to access and analyze US bank regulatory data from the FFIEC webservice.

**Prerequisites:**
- You must have an FFIEC webservice account (see :doc:`account_setup`).
- Install the package: `pip install ffiec-data-connect`
- Obtain your username and security token from the FFIEC portal (the security token is **not** your web portal password).

The examples below demonstrate common workflows, including authentication, retrieving reporting periods, listing filers, and downloading time series data. Each example assumes you have already set up your credentials and connection as shown in the first section.

.. note::
   If you encounter authentication errors, double-check your username and security token. The security token is **not** your web portal password. If you hit rate limits, try again later or implement retry logic.

Loading credentials and starting a connection to the FFIEC Webservice
---------------------------------------------------------------------
Credentials can be loaded from environment variables or by instantiating the `WebserviceCredentials` class directly.

.. code-block:: python

    from ffiec_data_connect import credentials, ffiec_connection
    
    creds = credentials.WebserviceCredentials(username="your_username", password="your_security_token")
    conn = ffiec_connection.FFIECConnection()

Collecting the reporting periods
-------------------------------
This example shows how to collect the reporting periods from the FFIEC Webservice. These reporting periods may be utilized for subsequent queries to the FFIEC Webservice, and to determine when new reporting periods are available for query.

Output is returned as a list of dates in the format of mm/dd/YYYY, which is the "native" format of the FFIEC Webservice.

.. code-block:: python

    from ffiec_data_connect import methods
    
    reporting_periods = methods.collect_reporting_periods(
        session=conn,
        creds=creds,
        output_type="list",
        date_output_format="string_original"
    )
    print(reporting_periods[0:5])

Expected output (first 5 reporting periods):

.. code-block:: text

    ['6/30/2022', '3/31/2022', '12/31/2021', '9/30/2021', '6/30/2021']

Collect the list of filers for a particular reporting period
-----------------------------------------------------------
This example shows how to collect the list of filers for a particular reporting period. Output is returned as a list of filers, with the "rssd" (the Federal Reserve's ID for regulations) as the primary key.

.. code-block:: python

    from ffiec_data_connect import methods
    
    filers = methods.collect_filers_on_reporting_period(
        session=conn,
        creds=creds,
        reporting_period="6/30/2022",
        output_type="list"
    )
    print(filers[100:102])

Expected output (sample):

.. code-block:: text

    [{'id_rssd': '5752005',
      'fdic_cert_number': '59322',
      'occ_chart_number': '25264',
      'ots_dock_number': None,
      'primary_aba_rout_number': None,
      'name': 'PEAK TRUST COMPANY, NATIONAL ASSOCIATION',
      'state': 'AK',
      'city': 'ANCHORAGE',
      'address': '3000 A STREET, SUITE 200',
      'filing_type': '041',
      'has_filed_for_reporting_period': False},
     ...]

.. list-table:: Output Fields
    :widths: 15 5 50
    :header-rows: 1

    * - Field
      - Description
      - Data Type
    * - id_rssd
      - The ID of the financial institution, as provided by the FFIEC.
      - string
    * - fdic_cert_number (optional)
      - The FDIC certificate number of the financial institution.
      - string
    * - occ_chart_number (optional)
      - The OCC ID of the financial institution.
      - string
    * - ots_dock_number (optional)
      - The OTS docket number of the financial institution.
      - string
    * - primary_aba_rout_number (optional)
      - The primary ABA routing number of the financial institution.
      - string
    * - name
      - The name of the financial institution.
      - string
    * - state
      - The state of the financial institution.
      - string
    * - city
      - The city of the financial institution.
      - string
    * - address
      - The address of the financial institution.
      - string
    * - filing_type
      - The type of filing for the financial institution (FFIEC 031, 041, or 051).
      - string
    * - has_filed_for_reporting_period
      - Whether or not the financial institution has filed for the reporting period.
      - boolean

Collect the rssd IDs and submission datetimes of all filers who have filed for a particular reporting period, since a particular date
-------------------------------------------------------------------------------------------------------------------------------
This example shows how to collect the rssd IDs of all filers who have filed for a particular reporting period, since a particular date. This method is useful for determining how many filers have completed their reporting for the reporting period, or have re-submitted.

.. code-block:: python

    from ffiec_data_connect import methods
    
    last_filing_date_time = methods.collect_filers_submission_date_time(
        session=conn,
        creds=creds,
        since_date="6/30/2022",
        reporting_period="6/30/2022",
    )
    print(last_filing_date_time)

Expected output (sample):

.. code-block:: text

    [{'rssd': 688556, 'datetime': '7/1/2022 12:15:06 AM'},
     {'rssd': 175458, 'datetime': '7/1/2022 8:00:37 AM'},
     ...]

.. note::
   The date and time of the last filing is in Washington DC time. If the requested date output format is `python_format`, the date and time will be converted to a ``datetime`` object, with the time zone set explicitly to ``America/New_York``.

Collect the list of rssd(s) that have filed in a reporting period since a particular date
---------------------------------------------------------------------------------------
This example shows how to collect the list of rssd(s) that have filed in a reporting period since a particular date. This list may be used for subsequent queries to the FFIEC Webservice.

.. code-block:: python

    from ffiec_data_connect import methods
    
    inst_list = methods.collect_filers_since_date(
        session=conn,
        creds=creds,
        since_date="6/30/2022",
        reporting_period="6/30/2022",
    )
    print(inst_list)

Expected output (sample):

.. code-block:: text

    [688556, 175458, 92144, 750444, 715630]

Collect the time series data associated with a particular rssd and reporting period
----------------------------------------------------------------------------------
With the metadata collected from the earlier examples, the following example shows how to collect the time series data associated with a particular rssd and reporting period. There are two time series that may be collected: "Call [Report]" and "UBPR" (Universal Bank Performance Report) data. Call Report data reflects the rolling data submissions of banks submitting their `FFIEC 031`, `FFIEC 041`, and `FFIEC 051` filings. UBPR data is released en masse for all banks mid-month, each month.

For more information on these reports and data, visit https://call.report

.. code-block:: python

    from ffiec_data_connect import methods
    
    time_series = methods.collect_data(
        session=conn,
        creds=creds,
        rssd_id="37",
        reporting_period="6/30/2022",
        series="call"
    )
    print(time_series[0:2])

Expected output (sample):

.. code-block:: text

    [{'mdrm': 'RCONK280',
      'rssd': '37',
      'quarter': '6/30/2022',
      'int_data': 0,
      'float_data': None,
      'bool_data': None,
      'str_data': None,
      'data_type': 'int'},
     {'mdrm': 'RCONB834',
      'rssd': '37',
      'quarter': '6/30/2022',
      'int_data': 0,
      'float_data': None,
      'bool_data': None,
      'str_data': None,
      'data_type': 'int'}]

.. list-table:: Output Fields
    :widths: 15 5 50
    :header-rows: 1

    * - Field
      - Description
      - Data Type
    * - mdrm
      - The ID code for the time series
      - string
    * - rssd
      - The Federal Reserve's ID for the reporting institution
      - string
    * - quarter
      - The quarter of the reporting period
      - string or datetime
    * - int_data
      - If present, the integer data for the time series
      - integer
    * - float_data
      - If present, the floating point data for the time series
      - float
    * - bool_data
      - If present, the boolean data for the time series
      - boolean
    * - str_data
      - If present, the string data for the time series
      - string
    * - data_type
      - The data type of the time series
      - string

.. note::
   The output is a list of dictionaries. For information on mapping the `MDRM` field to a descriptive data dictionary, visit https://call.report. Each row/record within a row/DataFrame will contain only one data_type, with the data type indicating which field within the dict/Series contains the data. The data_type field will be one of: int, float, bool, str.