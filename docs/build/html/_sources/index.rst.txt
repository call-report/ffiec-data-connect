.. FFIEC Webservice Python Connector documentation master file, created by
   sphinx-quickstart on Tue Jul 26 15:54:06 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to FFIEC Webservice Python Connector's documentation!
=============================================================

Repo: https://github.com/call-report/ffiec-data-connect

* **This package and documentation is not affiliated with the Federal Financial Institution Examination Council (FFIEC) or any other US Government Agency.**
* **Please review the license and disclaimer before using this package.**

The FFIEC Webservice Python Connector (`ffiec_data_connect`) was created to facilitate the use of the SOAP-based FFIEC Webservice.

Although limited documentation is provided for the Webservice by the FFIEC, practical use of the Webservice via Python requires a considerable amount of boilerplate code - and knowledge of esoteric terms and concepts inherent to bank regulatory data.

With these challenges in mind, this package provides a Python wrapper for the FFIEC Webservice, simplifying the process of interacting with the Webservice, and allow the rapid development of Python applications that require use of the data hosted on the Webservice.

Data returned from the Webservice may be returned as a native Python data structure (`list`) or Pandas DataFrames or Series.

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
