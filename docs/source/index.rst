.. FFIEC Webservice Python Connector documentation master file, created by
   sphinx-quickstart on Tue Jul 26 15:54:06 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to FFIEC Webservice Python Connector's documentation!
=============================================================

Repo: https://github.com/call-report/ffiec-data-connect

* **This package and documentation is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.**
* **Please review the license and disclaimer before using this package.**

Overview and Motivation
-----------------------
The FFIEC Webservice Python Connector (`ffiec_data_connect`) is an open-source library designed to make US bank regulatory data accessible and usable for data scientists, analysts, and developers. The FFIEC's SOAP-based webservice provides comprehensive regulatory data, but its interface is complex, poorly documented, and requires significant boilerplate code and domain knowledge to use effectively. This package abstracts away those complexities, offering a Pythonic API for interacting with the FFIEC webservice.

**Key Features:**
- Simple, high-level Python interface to the FFIEC SOAP webservice
- Retrieve data as native Python lists, or as Pandas/Polars DataFrames and Series for immediate analysis
- Credential management via environment variables or direct input
- Handles date normalization, data transformation, and error handling
- Practical examples and robust documentation
- Supports workflows such as:
  - Listing available reporting periods
  - Enumerating filers for a given period
  - Tracking submission times and statuses
  - Downloading time series data (Call Reports, UBPR, etc.)

**Intended Audience:**
- Data scientists, financial analysts, and developers working with US bank regulatory data
- Researchers and professionals seeking to automate or streamline access to FFIEC data

**Limitations & Disclaimers:**
- This project is independent and not affiliated with the FFIEC or any government agency
- Subject to FFIEC webservice rate limits and availability
- See the license and disclaimer for details on usage and liability

Additional Resources & Support
------------------------------

**Interactive Walkthrough:**
An interactive Jupyter Notebook, `example.ipynb`, is included in the project's [GitHub repository](https://github.com/call-report/ffiec-data-connect). It offers a hands-on guide to the connector's features and common use cases. To get started, simply clone the repository or download the notebook file and open it with Jupyter.

**Data Freshness:**
This connector leverages the FFIEC webservice, which typically provides financial data significantly faster (near real-time after submission) than the FFIEC's bulk data downloads (updated approximately monthly). This allows for more timely and up-to-date analysis.

**Community & Contributions:**
We welcome your feedback! If you encounter any bugs, have suggestions for new features, or wish to contribute to the project, please visit our [GitHub repository issues page](https://github.com/call-report/ffiec-data-connect/issues).

**Technical Assistance & Consulting:**
* **Academic & Non-Profit Users:** Limited, time-permitting technical assistance may be available from the author for users from academic, student, and non-profit organizations.
* **Commercial & Enterprise Users:** For for-profit entities, or those requiring more extensive support, custom feature development, or dedicated consulting, please reach out through the GitHub repository to discuss your needs.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   account_setup
   modules
   examples
   versionhistory
   licensedisclaimer


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
