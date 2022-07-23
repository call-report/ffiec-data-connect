"""Methods to utilize for inputting credentials for the FFIEC data connection.

This module provides secure methods for inputting credentials for the FFIEC webservice data connection.

Credentials may be input via environment variables, or passing them as arguments into the class structure. Wherever possible, the credentials should not be stored in source code.

"""

import requests
import sys
import os

from enum import Enum

from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport

from ffiec_data_connect import constants 

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
    
    def __init__(self, username = None, password = None):

        # if we are passing in credentials, use them
        if password and username:
            self.username = username
            self.password = password
            self.credential_source: CredentialType = CredentialType.SET_FROM_INIT
            return
        
        # do we have a username and password?
        if self.username is None or self.password is None:
        
            # do we have a environment variable for the username and password?
            # get the value of the env variable named "FFIEC_USERNAME"
            env_ffiec_username = os.environ.get("FFIEC_USERNAME")
            env_ffiec_password = os.environ.get("FFIEC_PASSWORD")
        
            # is env_ffiec_username and env_ffiec_password not None?
            if env_ffiec_username is not None and env_ffiec_password is not None:
            
                # set the username and password
                self.username = env_ffiec_username
                self.password = env_ffiec_password
                self.credential_source  = CredentialType.SET_FROM_ENV

            else:
                # we don't have a username and password, so raise an error
                self.credential_source = CredentialType.NO_CREDENTIALS
                raise ValueError("Username and password must be set to create a connection")
        
        else:
            self.credential_source = CredentialType.NO_CREDENTIALS
            return
        
        return
    
        
    def __str__(self) -> str:
        """String representation of the credentials."""
        if self.credential_source  == CredentialType.NO_CREDENTIALS or self.credential_source == None:
            return "No credentials set"
        elif self.credential_source == CredentialType.SET_FROM_INIT:
            return f"Credentials set from class initialization with username: {self.username}"         
        elif self.credential_source == CredentialType.SET_FROM_ENV:
            return f"Credentials set from environment variables with username: {self.username}"            
        else:
            return "Unknown credential source"
    
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
            raise ValueError("Username must be set")
        
        # check that we have a password
        if self.password is None:
            raise ValueError("Password must be set")
        
        # we have a user name and password, so try to log in
        # create the token
        wsse = UsernameToken(self.username, self.password)

        try:

            # create a transport
            transport = Transport(session=session)
            
            # create the client
            soap_client = Client(constants.WebserviceConstants.base_url, wsse=wsse, transport=transport)
            
            print("Standby...testing your access.")    
            
            has_access_response = soap_client.service.TestUserAccess()
            
            if has_access_response:
                print("Your credentials are valid.")
                return
            else:
                print("Your credentials are invalid. Please refer to the documentation for more information.")
                print(has_access_response)
                return
                
            print(has_access_response)
                
                        
        except Exception as e:
            print(
                "Credentials are invalid. Please check documentation for more information."
            )
            print("Credentials error: {}".format(e))
            
            raise(Exception("Credentials are invalid. Please check documentation for more information."))
        
        
    
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
        """
 
        self._username = username
        pass
    
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
        """
        self._password = password
        pass
