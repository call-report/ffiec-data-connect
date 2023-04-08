# FFIEC Data Connector

- The FFIEC Webservice Python Connector library (`ffiec_data_connect`) downloads data from the FFIEC (Federal Financial Institution Examination Council) via the FFIEC's "webservice" interface. 

- The library interfaces with the SOAP-based API published by FFIEC, normalizing dates and data, conducting transformations to permit immediate analysis of acquired data within a Python data science or scripted environment.


### Disclaimer

-  __This package and documentation is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.__
-  __Please review the license and disclaimer before using this package.__

### Overview

The FFIEC Webservice Python Connector (`ffiec_data_connect`) was created to facilitate the use of the SOAP-based FFIEC Webservice.

Although limited documentation is provided for the Webservice by the FFIEC, practical use of the Webservice via Python requires a considerable amount of boilerplate code - and knowledge of esoteric terms and concepts inherent to bank regulatory data.

With these challenges in mind, this package provides a Python wrapper for the FFIEC Webservice, simplifying the process of interacting with the Webservice, and allow the rapid development of Python applications that require use of the data hosted on the Webservice.

Data returned from the Webservice may be returned as a native Python data structure (`list`) or Pandas DataFrames or Series.

## Installation

``pip install ffiec-data-connect``

## Quickstart

1. To run this Quick Start, you must have an account on the FFIEC Webservice at https://cdr.ffiec.gov/public/PWS/CreateAccount.aspx?PWS=true
2. After you create an account, verify your password, and complete the sign-in process, log into the public web interface here: https://cdr.ffiec.gov/Public/PWS/Login.aspx
3. When you login, go to the "Account Details" tab. On this screen, look for the _Security Token_. This token is the password that you will use for the login credentials for ffiec-data-connect, __not the password__.

Sample code to login and collect reporting periods:

```
        from ffiec_data_connect import methods, credentials, ffiec_connection
        
        creds = credentials.WebserviceCredentials(username="USER_NAME_GOES_HERE", password="SECURITY_TOKEN_GOES_HERE")

        conn = ffiec_connection.FFIECConnection()

        reporting_periods = methods.collect_reporting_periods(
            session=conn,
            creds=creds,
            output_type="list",
            date_output_format="string_original"
        )
```
