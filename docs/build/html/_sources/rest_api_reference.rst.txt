REST API Reference
==================

This section provides a complete reference for the FFIEC CDR REST API endpoints. The API uses OAuth2 Bearer token authentication with JWT tokens that are valid for 90 days.

.. warning::
   **This is an UNOFFICIAL API Specification**

   This OpenAPI specification was reverse-engineered from official FFIEC documentation and extensive
   testing with the live API. While validated against actual API behavior, it should not be considered
   authoritative. The official documentation is CDR-PDD-SIS-611 v1.10.

.. important::
   **Non-Standard REST API Design**

   The FFIEC REST API deviates significantly from typical RESTful conventions:

   **Parameter Passing:**

   - ALL parameters are passed as **HTTP headers**, not query parameters or path parameters
   - This includes data that would typically be in the URL path (like RSSD IDs) or query string
   - Headers are **case-sensitive** and must match exactly (e.g., ``UserID`` not ``userid``)

   **HTTP Status Codes:**

   - Status codes **do not follow standard HTTP semantics**
   - Client errors often return 5xx codes instead of appropriate 4xx codes
   - Invalid requests may return 500 (Internal Server Error) instead of 400 (Bad Request)

   **Authentication Headers:**

   - ``UserID``: Your FFIEC PWS username (note capital 'ID')
   - ``Authentication``: Bearer {token} (NOT the standard ``Authorization`` header)
   - JWT tokens begin with ``ey`` and end with ``.``

.. note::
   **Why Use ffiec-data-connect?**

   The ``ffiec-data-connect`` library abstracts away these API complexities, providing:

   - Automatic header construction with correct casing
   - Proper error code translation and handling
   - Built-in retry logic for transient failures
   - Data type normalization and validation
   - A consistent, Pythonic interface

   This schema was developed during the creation of ffiec-data-connect and is provided as a
   reference for developers who need to understand the underlying API behavior.

Base URL
--------

Production: ``https://ffieccdr.azure-api.us/public``

Rate Limiting
-------------

- Maximum 2,500 requests per hour per user
- Rate limit resets on a rolling basis

API Specification
-----------------

The following OpenAPI specification documents all available REST API endpoints, request parameters, and response schemas:

.. openapi:: ../ffiec_rest_api_openapi.yaml

Common Response Codes
---------------------

.. list-table::
   :widths: 10 90
   :header-rows: 1

   * - Code
     - Description
   * - 200
     - Success - Request processed successfully
   * - 401
     - Unauthorized - Authentication failed or token expired
   * - 403
     - Forbidden - Invalid token or missing required headers
   * - 404
     - Not Found - Endpoint or resource not available
   * - 429
     - Too Many Requests - Rate limit exceeded (2500 requests/hour)
   * - 500
     - Internal Server Error - Server-side issue

Date Formats
------------

The REST API uses consistent date formatting:

- **Reporting periods**: ``MM/DD/YYYY`` (e.g., ``12/31/2024``)
- **DateTime values**: ``M/D/YYYY H:MM:SS AM/PM`` (e.g., ``2/20/2024 3:23:30 PM``)

Example Usage with Python
-------------------------

Using the ``ffiec_data_connect`` package:

.. code-block:: python

   from ffiec_data_connect import OAuth2Credentials
   from datetime import datetime, timedelta
   import ffiec_data_connect as fdc

   # Setup credentials
   creds = OAuth2Credentials(
       username="your_username",
       bearer_token="eyJhbGci...",  # Your JWT token
       token_expires=datetime.now() + timedelta(days=90)
   )

   # Collect reporting periods
   periods = fdc.collect_reporting_periods(
       session=None,  # None for REST API
       creds=creds,
       series="call",
       output_type="list"
   )

   # Collect data for a specific bank
   data = fdc.collect_data(
       session=None,
       creds=creds,
       rssd_id="37",
       reporting_period="12/31/2024",
       series="call"
   )

Direct API Usage with curl
---------------------------

.. code-block:: bash

   # Get reporting periods
   curl -X GET "https://ffieccdr.azure-api.us/public/RetrieveReportingPeriods" \
        -H "UserID: your_username" \
        -H "Authentication: Bearer eyJhbGci..." \
        -H "dataSeries: Call"

   # Get panel of reporters
   curl -X GET "https://ffieccdr.azure-api.us/public/RetrievePanelOfReporters" \
        -H "UserID: your_username" \
        -H "Authentication: Bearer eyJhbGci..." \
        -H "dataSeries: Call" \
        -H "reportingPeriodEndDate: 12/31/2024"

Migration from SOAP to REST
----------------------------

Key differences when migrating from SOAP:

1. **Authentication**: Use JWT tokens instead of username/password
2. **Headers**: All parameters in headers, not SOAP envelope
3. **Date Format**: Still uses ``MM/DD/YYYY`` format like SOAP
4. **Response Format**: JSON instead of XML/XBRL
5. **Performance**: Significantly faster response times

.. warning::
   The legacy SOAP API will be discontinued on **February 28, 2026**.
   All integrations must migrate to REST before this date.

Additional Resources
--------------------

- `REST API Specifications (PDF) <https://cdr.ffiec.gov/public/Files/SIS611_-_Retrieve_Public_Data_via_Web_Service.pdf>`_
- `CDR Help Desk <mailto:cdr.help@cdr.ffiec.gov>`_
- :doc:`account_setup` - Instructions for obtaining JWT tokens
- :doc:`examples` - Code examples using the REST API
