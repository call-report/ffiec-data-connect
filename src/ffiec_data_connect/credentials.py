"""Methods to utilize for inputting credentials for the FFIEC data connection.

This module provides secure methods for inputting credentials for the FFIEC webservice data connection.

Credentials may be input via environment variables, or passing them as arguments into the class structure. Wherever possible, the credentials should not be stored in source code.

"""

import os
import sys
from enum import Enum

import requests
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken

from ffiec_data_connect import constants, ffiec_connection
from ffiec_data_connect.exceptions import (
    ConnectionError,
    CredentialError,
    raise_exception,
)


class CredentialType(Enum):
    """Enumerated values that represent the methods through which credentials are provided to the FFIEC webservice via the package.

    Args:
        Enum (integer): Integer that represents the credential input method
    """

    NO_CREDENTIALS = 0
    SET_FROM_INIT = 1
    SET_FROM_ENV = 2


class WebserviceCredentials(object):
    """The WebserviceCredentials class. This class is used to store the credentials for the FFIEC webservice.

    Args:
        username (str, optional): FFIEC Webservice username. Optional: If not provided, the credentials will be set from the environment variable `FFIEC_USERNAME`
        password (str, optional): FFIEC Webservice password. Optional: If not provided, the credentials will be set from the environment variable `FFIEC_PASSWORD`

    Returns:
        WebserviceCredentials: An instance of the WebserviceCredentials class.

    """

    def __init__(self, username=None, password=None):
        # Flag to track if credentials are initialized (for immutability)
        self._initialized = False

        # collect the credentials from the environment variables
        # if the environment variables are not set, we will set the credentials from the arguments
        username_env = os.getenv("FFIEC_USERNAME")
        password_env = os.getenv("FFIEC_PASSWORD")

        # if we are passing in credentials, use them
        if password and username:
            self.username = username
            self.password = password
            self.credential_source: CredentialType = CredentialType.SET_FROM_INIT
            self._initialized = True  # Mark as initialized
            return

        # if not, check if we have the two environment variables

        # do we have both environment variables?
        elif username_env and password_env:
            self.username = username_env
            self.password = password_env
            self.credential_source: CredentialType = CredentialType.SET_FROM_ENV
            self._initialized = True  # Mark as initialized

        else:
            # do we have a username and password?
            self.credential_source = CredentialType.NO_CREDENTIALS

            # Provide helpful error message based on what's missing
            missing = []
            if not username and not username_env:
                missing.append("username (set via argument or FFIEC_USERNAME env var)")
            if not password and not password_env:
                missing.append("password (set via argument or FFIEC_PASSWORD env var)")

            raise_exception(
                CredentialError,
                f"Missing required credentials: {', '.join(missing)}",
                f"Missing required credentials: {', '.join(missing)}. "
                "Please provide credentials either as arguments or environment variables.",
                credential_source="none",
            )

        return

    def __str__(self) -> str:
        """String representation of the credentials - shows username but masks password for security."""
        if (
            self.credential_source == CredentialType.NO_CREDENTIALS
            or self.credential_source == None
        ):
            return "WebserviceCredentials(status='not configured')"

        # Show username plainly - usernames are not sensitive data
        username_display = (
            self.username
            if hasattr(self, "_username") and self._username
            else "not_set"
        )

        if self.credential_source == CredentialType.SET_FROM_INIT:
            return (
                f"WebserviceCredentials(source='init', username='{username_display}')"
            )
        elif self.credential_source == CredentialType.SET_FROM_ENV:
            return f"WebserviceCredentials(source='environment', username='{username_display}')"
        else:
            return "WebserviceCredentials(source='unknown')"

    def _mask_sensitive_string(self, value: str) -> str:
        """Mask sensitive string data, showing only first and last character."""
        if not value:
            return "***"
        if len(value) <= 2:
            return "*" * len(value)
        return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"

    def __repr__(self) -> str:
        return self.__str__()

    def test_credentials(self, session: requests.Session) -> bool:
        """Test the credentials with the FFIEC Webservice to determine if they are valid and accepted.

            | Note: The session argument can be generated directly from requests, or
            | using the helper class `FFIECConnection`


        Args:
            session (requests.Session): the connection to test the credentials

        Returns:
            bool: True if the credentials are valid, False otherwise

        Raises:
            ValueError: if the credentials are not set
            Exception: Other unspecified errors

        """

        # check that we have a user name
        if self.username is None:
            raise_exception(
                CredentialError,
                "Username is not set",
                "Username is not set. Please provide username via constructor or FFIEC_USERNAME environment variable.",
                credential_source=str(self.credential_source),
            )

        # check that we have a password
        if self.password is None:
            raise_exception(
                CredentialError,
                "Password is not set",
                "Password is not set. Please provide password via constructor or FFIEC_PASSWORD environment variable.",
                credential_source=str(self.credential_source),
            )

        # we have a user name and password, so try to log in
        try:
            # Use cached SOAP client for better performance
            from ffiec_data_connect.soap_cache import get_soap_client

            soap_client = get_soap_client(self, session)

            print("Standby...testing your access.")

            has_access_response = soap_client.service.TestUserAccess()

            if has_access_response:
                print("Your credentials are valid.")
                return
            else:
                print(
                    "Your credentials are invalid. Please refer to the documentation for more information."
                )
                print(has_access_response)
                return

            print(has_access_response)

        except Exception as e:
            # More descriptive error message
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise_exception(
                    CredentialError,
                    "Authentication failed",
                    "Authentication failed: Invalid username or password. "
                    "Please verify your FFIEC credentials are correct.",
                    credential_source=str(self.credential_source),
                )
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                raise_exception(
                    ConnectionError,
                    "Failed to connect to FFIEC webservice",
                    "Failed to connect to FFIEC webservice. "
                    "Please check your internet connection and proxy settings.",
                    url=constants.WebserviceConstants.base_url,
                )
            else:
                raise_exception(
                    CredentialError,
                    f"Failed to validate credentials: {error_msg}",
                    f"Failed to validate credentials: {error_msg}. "
                    "Please refer to https://cdr.ffiec.gov/public/PWS/Home.aspx for account setup.",
                    credential_source=str(self.credential_source),
                )

    @property
    def username(self) -> str:
        """Returns the username from the WebserviceCredentials instance.

        Returns:
            str: the username stored in the WebserviceCredentials instance
        """
        return self._username

    @username.setter
    def username(self, username: str) -> None:
        """Sets the username in the WebserviceCredentials instance.

        Args:
            username (str): the username to set in the WebserviceCredentials instance

        Raises:
            RuntimeError: If credentials are already initialized (immutable)
        """
        if getattr(self, "_initialized", False):
            from ffiec_data_connect.exceptions import CredentialError, raise_exception

            raise_exception(
                CredentialError,
                "Cannot modify username after initialization",
                "Cannot modify username after initialization. WebserviceCredentials are immutable for security.",
                credential_source=str(getattr(self, "credential_source", "unknown")),
            )

        self._username = username

    @property
    def password(self) -> str:
        """Returns the password from the WebserviceCredentials instance.

        Returns:
            str: the password stored in the WebserviceCredentials instance
        """
        return self._password

    @password.setter
    def password(self, password: str) -> None:
        """Sets the password in the WebserviceCredentials instance.

        Args:
            password (str): the password to set in the WebserviceCredentials instance

        Raises:
            RuntimeError: If credentials are already initialized (immutable)
        """
        if getattr(self, "_initialized", False):
            from ffiec_data_connect.exceptions import CredentialError, raise_exception

            raise_exception(
                CredentialError,
                "Cannot modify password after initialization",
                "Cannot modify password after initialization. WebserviceCredentials are immutable for security.",
                credential_source=str(getattr(self, "credential_source", "unknown")),
            )

        self._password = password
