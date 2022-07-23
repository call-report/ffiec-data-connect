FFIEC Data Connector
=============================================================

About
-----

Repo: https://github.com/call-report/ffiec-data-connect
Documentation: https://ffiec-data-connect.readthedocs.io/en/latest/

* **This package and documentation is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.**
* **Please review the license and disclaimer before using this package.**

The FFIEC Webservice Python Connector (`ffiec_data_connect`) was created to facilitate the use of the SOAP-based FFIEC Webservice.

Although limited documentation is provided for the Webservice by the FFIEC, practical use of the Webservice via Python requires a considerable amount of boilerplate code - and knowledge of esoteric terms and concepts inherent to bank regulatory data.

With these challenges in mind, this package provides a Python wrapper for the FFIEC Webservice, simplifying the process of interacting with the Webservice, and allow the rapid development of Python applications that require use of the data hosted on the Webservice.

Data returned from the Webservice may be returned as a native Python data structure (`list`) or Pandas DataFrames or Series.

Installing
----------
``pip install ffiec-data-connect``

Quick Start
-----------

        from ffiec_data_connect import methods, credentials, ffiec_connetion
        
        creds = credentials.WebserviceCredentials(username="user1234", password="password1234")

        conn = ffiec_connection.FFIECConnection()

        reporting_periods = methods.collect_reporting_periods(
            session=conn,
            creds=creds,
            output_type="list",
            date_output_format="string_original"
        )




