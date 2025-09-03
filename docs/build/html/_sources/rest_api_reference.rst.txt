REST API Reference
==================

This section provides a complete reference for the FFIEC CDR REST API endpoints. The API uses OAuth2 Bearer token authentication with JWT tokens that are valid for 90 days.

.. important::
   **Authentication Requirements**
   
   - All parameters are passed as **HTTP headers**, not query parameters
   - ``UserID``: Your FFIEC PWS username (note capital 'ID')
   - ``Authentication``: Bearer {token} (NOT Authorization header)
   - JWT tokens begin with ``ey`` and end with ``.``

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