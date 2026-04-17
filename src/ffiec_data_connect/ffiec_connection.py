# SPDX-License-Identifier: MPL-2.0
# Copyright 2025-2026 Civic Forge Solutions LLC

"""FFIECConnection - DEPRECATED.

The FFIEC SOAP API was shut down on February 28, 2026.
This module is retained for import compatibility only.
"""

from enum import Enum

from ffiec_data_connect.exceptions import SOAPDeprecationError


class ProxyProtocol(Enum):
    """Enumerated values that represent the proxy protocol options.

    Deprecated: Proxy configuration was only used with the SOAP API.
    """

    HTTP = 0
    HTTPS = 1


class FFIECConnection:
    """Deprecated. The FFIEC SOAP API was shut down on February 28, 2026.

    This class is retained for import compatibility only.
    Instantiation raises SOAPDeprecationError.
    """

    def __init__(self) -> None:
        raise SOAPDeprecationError(
            soap_method="FFIECConnection",
            rest_equivalent="Pass session=None to all methods",
            code_example=(
                "  from ffiec_data_connect import OAuth2Credentials, collect_data\n"
                "\n"
                "  # Get a token at: https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx\n"
                "  creds = OAuth2Credentials(\n"
                '      username="your_ffiec_username",\n'
                '      bearer_token="eyJ...",  # 90-day JWT from FFIEC portal\n'
                "  )\n"
                "\n"
                "  # No FFIECConnection needed -- pass session=None\n"
                "  data = collect_data(\n"
                "      session=None, creds=creds,\n"
                '      reporting_period="12/31/2025", rssd_id="480228",\n'
                '      series="call", output_type="pandas"\n'
                "  )"
            ),
        )
