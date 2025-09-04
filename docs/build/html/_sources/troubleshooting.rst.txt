===============
Troubleshooting
===============

This guide covers common issues and their solutions when using the FFIEC Data Connect library.

Authentication Issues
=====================

JWT Token Problems
------------------

**"Invalid bearer token" or Authentication Failed**

.. error::
   **Symptom**: Getting authentication errors despite having valid credentials

   **Common Causes**:

   1. **Using website password instead of JWT token**

      ❌ **Wrong**: Using your FFIEC account password

      ✅ **Correct**: Using the JWT token generated from your PWS account

   2. **Token expiration**

      - JWT tokens expire after **90 days**
      - Tokens are considered expired if they expire within **24 hours** (warning threshold)
      - Check your token expiration date in the PWS portal

   3. **Invalid token format**

      - Valid JWT tokens **must start with** ``ey``
      - Valid JWT tokens **must end with** ``.``
      - Minimum length: 20 characters
      - Example: ``eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4ifQ.``

**Solution**:

.. code-block:: python

   from ffiec_data_connect import OAuth2Credentials
   from datetime import datetime, timedelta

   # Check your token format and expiration
   creds = OAuth2Credentials(
       username="your_username",
       bearer_token="eyJhbGci...",  # JWT token, NOT password!
       token_expires=datetime.now() + timedelta(days=90)
   )

   # Check if token is expired
   if creds.is_expired:
       print("Token is expired or expires within 24 hours - generate a new one!")

Header Name Issues
------------------

**"Authentication header not recognized"**

.. error::
   **Symptom**: REST API returns authentication errors despite valid token

   **Common Causes**:

   1. **Wrong header name**: Using ``Authorization`` instead of ``Authentication``
   2. **Case sensitivity**: Using ``userid`` instead of ``UserID``

The FFIEC REST API uses non-standard header names:

.. list-table:: Correct REST API Headers
   :widths: 30 70
   :header-rows: 1

   * - Header Name
     - Purpose
   * - ``UserID``
     - Your FFIEC username (note capital 'ID')
   * - ``Authentication``
     - Bearer token (NOT ``Authorization``)

**Solution**: The library handles this automatically, but if making direct API calls:

.. code-block:: python

   headers = {
       "UserID": "your_username",           # Not "userid" or "UserId"
       "Authentication": "Bearer token...",  # Not "Authorization"
       "dataSeries": "Call"
   }

Account Setup Issues
====================

Microsoft Callback Link Problems
---------------------------------

.. error::
   **Symptom**: After completing Microsoft verification, you see a blank page or error

   **Solution**: Manually navigate to the login page:

   https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx

This is a known issue with the Microsoft Entra ID callback process.

Migration Failures
-------------------

**"Migration invitation link doesn't work"**

.. error::
   **Symptom**: Cannot complete account migration from invitation email

   **Solutions**:

   1. **Try again**: Some migrations fail on first attempt
   2. **Clear browser cache** and try the invitation link again
   3. **Create new account**: If migration continues to fail, create a new account instead
   4. **Contact help desk**: cdr.help@cdr.ffiec.gov

**After successful migration**:

.. warning::
   You **MUST generate a new JWT token** after migration. Old tokens become invalid immediately.

Token Generation Issues
-----------------------

**"Cannot find token generation option"**

1. Log into https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx
2. Navigate to **Account Details** or **Token Management** tab
3. Look for **Generate Token** or **REST API Token** section
4. New tokens are valid for 90 days

API Usage Issues
================

SOAP vs REST Confusion
-----------------------

.. list-table:: API Comparison
   :widths: 20 40 40
   :header-rows: 1

   * - Aspect
     - SOAP (Legacy)
     - REST (Modern)
   * - **Credentials**
     - ``WebserviceCredentials(username, password)``
     - ``OAuth2Credentials(username, token, expires)``
   * - **Session**
     - ``FFIECConnection()`` object required
     - ``None`` (no session needed)
   * - **Date Format**
     - ``MM/DD/YYYY`` (e.g., "12/31/2023")
     - ``MM/DD/YYYY`` (e.g., "12/31/2023")
   * - **Rate Limit**
     - 1,000 requests/hour
     - 2,500 requests/hour
   * - **Status**
     - ⚠️ **Deprecated Feb 28, 2026**
     - ✅ **Recommended**

**Solution**: Use REST API for new implementations:

.. code-block:: python

   # ✅ REST API (Recommended)
   from ffiec_data_connect import OAuth2Credentials, collect_data

   creds = OAuth2Credentials(username="...", bearer_token="...", token_expires=...)
   data = collect_data(session=None, creds=creds, rssd_id="...",
                       reporting_period="...", series="call")  # session=None for REST

   # ❌ SOAP API (Deprecated)
   from ffiec_data_connect import WebserviceCredentials, FFIECConnection

   creds = WebserviceCredentials(username="...", password="...")
   session = FFIECConnection()
   data = collect_data(session=session, creds=creds, ...)

Data Issues
===========

Integer Display with Decimals
------------------------------

**"My integer data shows as 100.0 instead of 100"**

.. error::
   **Symptom**: Integer values display with decimal points (e.g., ``100.0`` instead of ``100``)

   **Cause**: Default null handling uses ``np.nan`` which converts integers to floats

   **Solution**: Use ``force_null_types="pandas"`` parameter:

.. code-block:: python

   # Force pandas null handling for better integer display
   data = collect_data(
       session=None,
       creds=rest_creds,
       rssd_id="12345",
       reporting_period="2023-12-31",
       series="call",
       force_null_types="pandas"  # Keeps integers as integers
   )

Empty Datasets
--------------

**"collect_data returns empty list"**

.. error::
   **Common Causes**:

   1. **Wrong reporting period**: Institution didn't file for that period
   2. **Wrong RSSD ID**: Institution ID doesn't exist or is inactive
   3. **Wrong series**: Requesting "ubpr" for institution that doesn't have UBPR data
   4. **Invalid date format**: Both APIs use MM/DD/YYYY format

**Debugging Steps**:

.. code-block:: python

   # 1. Check if institution exists in the reporting period
   filers = collect_filers_on_reporting_period(
       session=None, creds=creds, reporting_period="2023-12-31"
   )
   your_rssd = "12345"
   institution_exists = any(filer['id_rssd'] == your_rssd for filer in filers)

   # 2. Check available reporting periods
   periods = collect_reporting_periods(session=None, creds=creds, series="call")
   print(f"Available periods: {periods[:5]}")  # Show first 5

   # 3. Try different series
   for series in ["call", "ubpr"]:
       try:
           data = collect_data(..., series=series)
           print(f"{series}: {len(data)} records")
       except Exception as e:
           print(f"{series}: {e}")

Common Error Messages
=====================

HTTP Status Codes
------------------

.. list-table:: Common HTTP Errors
   :widths: 10 30 60
   :header-rows: 1

   * - Code
     - Meaning
     - Solutions
   * - 401
     - Unauthorized
     - Check token validity, regenerate if expired
   * - 403
     - Forbidden
     - Verify headers are correct (``UserID``, ``Authentication``)
   * - 404
     - Not Found
     - Check endpoint URL, verify RSSD ID exists
   * - 429
     - Rate Limited
     - Wait before next request, consider using REST (higher limits)
   * - 500
     - Server Error
     - Often client error (invalid params), check request format

Library Error Messages
-----------------------

.. error::
   **"Bearer token appears invalid (too short)"**

   Token must be at least 20 characters. Ensure you copied the complete JWT token.

.. error::
   **"JWT token must start with 'ey' and end with '.'"**

   Invalid token format. Generate a new token from PWS portal.

.. error::
   **"Token is expired or expires within 24 hours"**

   Generate a new 90-day token from your PWS account.

.. error::
   **"force_null_types must be 'numpy' or 'pandas'"**

   Invalid parameter value. Use ``force_null_types="pandas"`` for better integer display.

Performance Issues
==================

Slow Response Times
-------------------

**"API calls are very slow"**

**Solutions**:

1. **Use REST API** instead of SOAP (significantly faster)
2. **Check rate limits**: Don't exceed 2,500 requests/hour (REST) or 1,000/hour (SOAP)
3. **Use session reuse** for SOAP (automatic in library)
4. **Consider AsyncCompatibleClient** for concurrent requests

.. code-block:: python

   # For high-performance scenarios
   from ffiec_data_connect import AsyncCompatibleClient

   async with AsyncCompatibleClient(creds) as client:
       tasks = [
           client.collect_data_async(rssd_id=rssd, reporting_period="...", series="call")
           for rssd in rssd_list
       ]
       results = await asyncio.gather(*tasks)

Memory Issues
-------------

**"Out of memory when processing large datasets"**

1. **Use ``output_type="polars"``** for better memory efficiency
2. **Process in batches** rather than all at once
3. **Use specific date ranges** instead of all available periods

Migration and Legacy Issues
===========================

SOAP to REST Migration
-----------------------

**"How do I migrate from SOAP to REST?"**

.. list-table:: Migration Checklist
   :widths: 50 50
   :header-rows: 1

   * - SOAP (Old)
     - REST (New)
   * - Generate Security Token
     - Generate JWT Token (90-day)
   * - ``WebserviceCredentials(user, password)``
     - ``OAuth2Credentials(user, token, expires)``
   * - ``FFIECConnection()`` session
     - ``session=None``
   * - Date: ``"12/31/2023"``
     - Date: ``"12/31/2023"``
   * - Rate limit: 1,000/hour
     - Rate limit: 2,500/hour

**Migration Code Example**:

.. code-block:: python

   # Before (SOAP)
   from ffiec_data_connect import WebserviceCredentials, FFIECConnection

   soap_creds = WebserviceCredentials("user", "password")
   soap_session = FFIECConnection()
   data = collect_data(soap_session, soap_creds, reporting_period="12/31/2023",
                       rssd_id="...", series="call")

   # After (REST)
   from ffiec_data_connect import OAuth2Credentials

   rest_creds = OAuth2Credentials("user", "jwt_token", expires_date)
   data = collect_data(None, rest_creds, reporting_period="12/31/2023", ...)

Legacy Token Expiration
------------------------

.. warning::
   **Important**: All legacy SOAP security tokens will expire on **February 28, 2026**.

   You must migrate to REST API before this date.

Getting Help
============

Support Channels
-----------------

.. important::
   **The FFIEC does NOT provide technical support for this library.** FFIEC support is only available for matters relating to your CDR account.

**FFIEC Support (Account Issues Only)**

Contact the FFIEC Help Desk (cdr.help@cdr.ffiec.gov) **ONLY** for:

- CDR account setup and migration issues
- PWS portal access problems
- JWT token generation problems
- Questions about official data availability and reporting schedules
- Microsoft Entra ID authentication issues

**Library Support (Technical Issues)**

For technical support with the ffiec-data-connect library:

1. **GitHub Issues** (Recommended): https://github.com/call-report/ffiec-data-connect/issues

   - Search existing issues before creating a new one
   - Include complete error messages and code examples
   - Best for bugs, feature requests, and general questions

2. **Direct Email**: michael@civicforge.solutions

   - For urgent issues or private inquiries
   - Basic support provided free for all users

**Commercial Support**

For commercial entities requiring:

- **Priority technical support** with guaranteed response times
- **Custom code modifications** and feature development
- **Integration consulting** and architectural guidance
- **Training and onboarding** for development teams
- **Private deployment** and customization services

Enhanced commercial support is available upon request. Contact michael@civicforge.solutions to discuss your specific requirements and support packages.

**Before contacting any support**:

1. Check this troubleshooting guide thoroughly
2. Verify your credentials are valid and not expired
3. Test with different RSSD IDs or reporting periods
4. Review existing GitHub issues for similar problems

Debug Information to Provide
-----------------------------

When reporting issues, include:

.. code-block:: python

   import ffiec_data_connect as fdc
   print(f"Library version: {fdc.__version__}")
   print(f"Python version: {sys.version}")
   print(f"Credential type: {type(creds).__name__}")

   # For REST credentials
   if hasattr(creds, 'is_expired'):
       print(f"Token expired: {creds.is_expired}")

**Include**:
- Complete error messages and stack traces
- Anonymized code snippets showing the issue
- RSSD ID and reporting period (if data-related)
- Whether using SOAP or REST API

Additional Resources
====================

- **Official FFIEC Documentation**: CDR-PDD-SIS-611 v1.10
- **Library Documentation**: https://ffiec-data-connect.readthedocs.io/
- **GitHub Repository**: https://github.com/call-report/ffiec-data-connect
- **REST API Reference**: :doc:`rest_api_reference`
- **Account Setup**: :doc:`account_setup`
- **Examples**: :doc:`examples`
