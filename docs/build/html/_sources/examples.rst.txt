Examples & Interactive Tutorials
==================================

Interactive Jupyter Notebook Demos
-----------------------------------

📓 **Comprehensive Tutorial Notebooks**

The library includes two detailed Jupyter notebook tutorials with executable examples and real data:

🚀 **REST API Demo** (``ffiec_data_connect_rest_demo.ipynb``)
    Complete walkthrough of the modern REST API including:
    
    * OAuth2 credential setup and JWT token management
    * Authentication troubleshooting and token validation  
    * All 7 REST API endpoints with real banking data examples
    * Performance optimization and rate limiting strategies
    * Advanced features: batch operations, error handling
    * Migration from SOAP to REST API

🔧 **SOAP API Demo** (``ffiec_data_connect_soap_demo.ipynb``)
    Legacy SOAP API implementation covering:
    
    * WebserviceCredentials setup and session management
    * Connection handling and error recovery
    * Historical data collection examples
    * Comparison with REST API functionality
    * Step-by-step migration guidance

💡 **Getting Started with Notebooks**
    1. Install the library: ``pip install ffiec-data-connect``
    2. Open the notebooks in your preferred environment (Jupyter Lab, VS Code, Colab)
    3. Follow the step-by-step instructions with executable code cells
    4. Experiment with your own credentials and data queries

Code Examples
=============

Loading credentials and starting a connection to the FFIEC Webservice
---------------------------------------------------------------------
When using the package, credentials to the Webservice may be loaded from environment variables, or through the instantiation of the `WebserviceCredentials` class.


The following example shows how to load credentials from instantiation (note that the username and password included are placeholders)::

    from ffiec_data_connect import credentials, ffiec_connection


    creds = credentials.WebserviceCredentials(username="user1234", password="password1234")

    conn = ffiec_connection.FFIECConnection()

Collecting the reporting periods
================================

The following example shows how to collect the reporting periods from the FFIEC Webservice.

These reporting periods may be utilized for subsequent queries to the FFIEC Webservice, and to determine when new reporting periods are available for query.

Output is returned as a list of dates in the format of mm/dd/YYYY, which is the "native" format of the FFIEC Webservice.

This code example assumes that a `FFIECConnection` object named ``conn`` and `WebserviceCredentials` object named ``creds`` has been instantiated. (See previous example) ::

        from ffiec_data_connect import methods

        reporting_periods = methods.collect_reporting_periods(
            session=conn,
            creds=creds,
            output_type="list",
            date_output_format="string_original"
        )

        print(reporting_periods[0:5])

        >> ['6/30/2022', '3/31/2022', '12/31/2021', '9/30/2021', '6/30/2021']

Collect the list of filers for a particular reporting period
=============================================================

    The following example shows how to collect the list of filers for a particular reporting period.

    This list of filers may be utilized for subsequent queries to the FFIEC Webservice, and to determine which filers are available for query.

    Output is returned as a list of filers, with the "rssd" (the name of the Federal Reserve's ID for regulations) as the primary key.

    Note that due to the nature of the FFIEC Webservice, the list of filers may be very large. As a result, the wall time for this query may be very long, depending on the size of the list of filers, the speed of the connection, and the server load of the FFIEC Webservice.

    `A data dictionary for the output is provided below the output`

    This code example assumes that a `FFIECConnection` object named ``conn`` and `WebserviceCredentials` object named ``creds`` has been instantiated. (See previous example) ::

        from ffiec_data_connect import methods

        filers = methods.collect_filers_on_reporting_period(
            session=conn,
            creds=creds,
            reporting_period="6/30/2022",
            output_type="list"
        )

        print(filers[100:102])

        >>
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

        {'id_rssd': '114260',
        'fdic_cert_number': '16130',
        'occ_chart_number': '12072',
        'ots_dock_number': None,
        'primary_aba_rout_number': '125200060',
        'name': 'FIRST NATIONAL BANK ALASKA',
        'state': 'AK',
        'city': 'ANCHORAGE',
        'address': '360 K STREET',
        'filing_type': '041',
        'has_filed_for_reporting_period': False}]


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

Collect the rssd IDs and submission datetimes of all filers who have filed for a particular reporting period, since a particular date.
======================================================================================================================================

    The following example shows how to collect the rssd IDs of all filers who have filed for a particular reporting period, since a particular date.

    This method is useful for determining how many filers have completed their reporting for the reporting period.

    Filers may also re-submit their filings for the reporting period, so this method may also be useful for determining which and how many filers have re-submitted.


    This code example assumes that a `FFIECConnection` object named ``conn`` and `WebserviceCredentials` object named ``creds`` has been instantiated. (See previous example) ::

        from ffiec_data_connect import methods

        last_filing_date_time = methods.collect_filers_submission_date_time(
            session=conn,
            creds=creds,
            since_date="6/30/2022",
            reporting_period="6/30/2022",
        )

        print(last_filing_date_time)

        >> [{'rssd': 688556, 'datetime': '7/1/2022 12:15:06 AM'},
            {'rssd': 175458, 'datetime': '7/1/2022 8:00:37 AM'},
            {'rssd': 92144, 'datetime': '7/1/2022 12:25:04 PM'},
            {'rssd': 750444, 'datetime': '7/1/2022 4:41:37 PM'},
            {'rssd': 715630, 'datetime': '7/2/2022 12:08:13 PM'}]

    The method outputs a list of rssd(s), which represents the Federal Reserve's ID for regulated institutions, and the date and time of the last filing for the reporting period.

    Note that the date and time of the last filing is in Washington DC time. If the requested date output format is `python_format`, the date and time will be converted to a ``datetime`` object, with the time zone set explicitly to ``America/NewYork``.


Collect the list of rssd(s) that have filed in a reporting period since a particular date.
==========================================================================================

    The following example shows how to collect the list of rssd(s) that have filed in a reporting period since a particular date.

    This list of rssd(s) may be utilized for subsequent queries to the FFIEC Webservice, and to determine which rssd(s) have filed for the reporting period.

    The difference between this example and the prior example is that this example only returns a list of RSSDs, not a list of RSSDs and the RSSD's last filing date and time.

    This code example assumes that a `FFIECConnection` object named ``conn`` and `WebserviceCredentials` object named ``creds`` has been instantiated. (See previous example) ::

        from ffiec_data_connect import methods

        inst_list = methods.collect_filers_since_date(
            session=conn,
            creds=creds,
            since_date="6/30/2022",
            reporting_period="6/30/2022",
        )

        print(inst_list)

        >> [688556, 175458, 92144, 750444, 715630]


REST API Examples
=================

The package also supports the modern REST API using OAuth2 credentials. Here are examples using the REST API:

**Loading OAuth2 credentials and connecting**::

    from ffiec_data_connect import OAuth2Credentials
    from datetime import datetime, timedelta

    # Create OAuth2 credentials for REST API
    rest_creds = OAuth2Credentials(
        username="your_username",
        bearer_token="your_bearer_token",
        token_expires=datetime.now() + timedelta(days=90)
    )

    # No connection object needed for REST - pass None as session

**Collecting reporting periods via REST**::

    from ffiec_data_connect import methods

    reporting_periods = methods.collect_reporting_periods(
        session=None,  # None for REST API
        creds=rest_creds,
        output_type="list",
        date_output_format="string_original"
    )

    print(reporting_periods[0:5])
    >> ['2024-09-30', '2024-06-30', '2024-03-31', '2023-12-31', '2023-09-30']

**Collecting data via REST with force_null_types**::

    # Collect data with pandas null handling (better for integer display)
    time_series = methods.collect_data(
        session=None,
        creds=rest_creds,
        rssd_id="37",
        reporting_period="2024-06-30",
        series="call",
        force_null_types="pandas"  # Use pd.NA for nulls
    )

    # Or force numpy nulls for compatibility
    time_series_compat = methods.collect_data(
        session=None,
        creds=rest_creds,
        rssd_id="37",
        reporting_period="2024-06-30",
        series="call",
        force_null_types="numpy"  # Use np.nan for nulls
    )

**REST API Advantages**:

* Better performance and reliability
* Modern authentication with OAuth2
* Automatic retry logic built-in
* No session management required


Collect the time series data associated with a particular rssd and reporting period.
====================================================================================

    With the metadata collected from the earlier examples, the following example shows how to collect the time series data associated with a particular rssd and reporting period.

    There are two time series that may be collected: "Call [Report]" and "UBPR" (Universal Bank Performance Report) data. Call Report data reflects the rolling data submissions of banks submitting their `FFIEC 031`, `FFIEC 041`, and `FFIEC 051` filings. UBPR data is released en masse for all banks mid-month, each month.

    (For more information on these reports and data, visit https://call.report)

    This code example assumes that a `FFIECConnection` object named ``conn`` and `WebserviceCredentials` object named ``creds`` has been instantiated. (See previous example) ::

        from ffiec_data_connect import methods

        time_series = methods.collect_data(
            session=conn,
            creds=creds,
            rssd_id="37",
            reporting_period="6/30/2022",
            series="call"
        )

        print(time_series[0:2])

        >>
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

    Note on output:

    * The output is a list of dictionaries.
    * For information on mapping the `MDRM` field to a descriptive data dictionary,
      visit https://call.report
    * Each row/record within a row/DataFrame will contain only one data_type,
      with the data type indicating which field within the dict/Series contains the data.
    * The data_type field will be one of the following:
      * int
      * float
      * bool
      * str
