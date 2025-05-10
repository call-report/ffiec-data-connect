FFIEC Account Setup Instructions
===============================

Prerequisites for ffiec_data_connect package
-------------------------------------------
To utilize the `ffiec_data_connect` package, you must create a **PDD account** (not a "public web login") with the Federal Financial Institution Examination Council (FFIEC)'s Webservice portal.

- There is no cost for the account, nor are there any apparent maximum limits for the total amount of data downloaded. Users are advised to read the terms of service and privacy policy before applying for a user name and utilizing the service.
- The FFIEC webservice enforces unpublished rate limits. When utilizing the package, it is recommended to implement retry logic in your code in case the rate limit is exceeded.
- Please note that support for use of FFIEC accounts is provided by the FFIEC, and is not provided by the `ffiec_data_connect` package repository.

**Important:**
- You must create a **PDD account**. Do *not* create a "public web login" account, as it will not work with the API or this package.
- After registering, you will receive an email from the FFIEC containing your **web token**. This web token is what you must use as your password in the `ffiec_data_connect` library. **Do not use your web portal password.**

How to create a PDD account
---------------------------

1. Visit the website at https://cdr.ffiec.gov/public/PWS/CreateAccount.aspx?PWS=true
2. Complete the fields requested, making sure to select the option to create a **PDD account**.
3. After registration, check your email for a message from the FFIEC. This email will contain your **web token**.
4. Use your username and the web token (not your web portal password) with the `ffiec_data_connect` package.

.. image:: images/create_account.png
  :width: 400
  :alt: Screen shot of FFIEC account creation page
