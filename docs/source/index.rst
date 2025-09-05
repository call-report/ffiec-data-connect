.. FFIEC Webservice Python Connector documentation master file, created by
   sphinx-quickstart on Tue Jul 26 15:54:06 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to FFIEC Webservice Python Connector's documentation!
=============================================================

Repo: https://github.com/call-report/ffiec-data-connect

* **This package and documentation is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.**
* **Please review the license and disclaimer before using this package.**

The FFIEC Webservice Python Connector (`ffiec_data_connect`) was created to facilitate the use of both the SOAP-based FFIEC Webservice and the modern REST API.

Although limited documentation is provided for the Webservice by the FFIEC, practical use of the Webservice via Python requires a considerable amount of boilerplate code - and knowledge of esoteric terms and concepts inherent to bank regulatory data.

With these challenges in mind, this package provides a Python wrapper for both FFIEC APIs:

* **SOAP API**: The legacy webservice using WebserviceCredentials (username/password)
* **REST API**: The modern API using OAuth2Credentials (bearer tokens)

Both APIs provide access to the same data, with the REST API offering improved performance and reliability. The package automatically handles protocol differences, providing a unified interface for data collection.

Data returned from the APIs may be returned as:

* Native Python data structures (`list`)
* Pandas DataFrames or Series
* Polars DataFrames (with direct XBRL conversion for maximum precision)

Getting Started with Interactive Tutorials
===========================================

📓 **Jupyter Notebook Demos**

The best way to learn the library is through our comprehensive Jupyter notebook tutorials:

* **``ffiec_data_connect_rest_demo.ipynb``** - Complete REST API walkthrough with executable examples
* **``ffiec_data_connect_soap_demo.ipynb``** - Legacy SOAP API implementation and migration guidance

These notebooks include:

* Step-by-step setup instructions with real credentials
* Executable code examples using actual banking data  
* Troubleshooting guides for common issues
* Performance optimization techniques
* Migration strategies from SOAP to REST

The notebooks are included with the package installation and provide hands-on experience with both APIs.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   account_setup
   development_setup
   modules
   rest_api_reference
   data_type_handling
   examples
   troubleshooting
   versionhistory
   licensedisclaimer


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
