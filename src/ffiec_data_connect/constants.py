"""Constant values utilized for data collection and other purposes.

This module contains constant values that are unlikely to change,
but need to be referenced by other modules.

"""


class WebserviceConstants(object):
    """The URL endpoint for the FFIEC SOAP-based webservice."""

    base_url = "https://cdr.ffiec.gov/Public/PWS/WebServices/RetrievalService.asmx?WSDL"
