"""Methods to utilize for inputting credentials for the FFIEC data connection.

This module provides secure methods for inputting credentials for the FFIEC webservice data connection.

Credentials may be input via environment variables, or passing them as arguments into the class structure. Wherever possible, the credentials should not be stored in source code.

"""

import requests
import sys
import os
import operator
from enum import Enum

from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.transports import Transport

from ffiec_data_connect import constants, ffiec_connection

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

        # collect the credentials from the environment variables
        # if the environment variables are not set, we will set the credentials from the arguments
        username_env = os.getenv("FFIEC_USERNAME")
        password_env = os.getenv("FFIEC_PASSWORD")

        # if we are passing in credentials, use them
        if password and username:
            self.username = username
            self.password = password
            self.credential_source: CredentialType = CredentialType.SET_FROM_INIT
            return
        
        # if not, check if we have the two environment variables
        
        # do we have both environment variables?
        elif username_env and password_env:
            self.username = username_env
            self.password = password_env
            self.credential_source: CredentialType = CredentialType.SET_FROM_ENV
        
        else:
            # do we have a username and password?
            self.credential_source = CredentialType.NO_CREDENTIALS

            raise ValueError("Username and password must be set to create a connection")
        
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

    def return_all_services_and_methods(self, session: requests.Session) -> None:
        """Returns all services and methods for the FFIEC Webservice.
        
        Args:
            session (requests.Session): the connection to the FFIEC Webservice
        """
    
        # create the wsse token
        wsse = UsernameToken(self.username, self.password)
        
        # create the transport
        transport = Transport(session=session)
        
        # create the client
        soap_client = Client(constants.WebserviceConstants.base_url, wsse=wsse, transport=transport)
    

        for service in soap_client.wsdl.services.values():
            print(f"Service: {service.name}")
            for port in service.ports.values():
                operations = sorted(port.binding._operations.values(), key=operator.attrgetter('name'))
                for operation in operations:
                    print(f"  Method: {operation.name}")
                    print(f"    Input: {operation.input.signature()}")
                    print(f"    Output: {operation.output.signature()}")  # Added output signature
                    print("--------------------------------")
            pass
        
    

        
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
            transport = None
            
            if isinstance(session, requests.Session):
                transport = Transport(session=session)                
            elif isinstance(session, ffiec_connection.FFIECConnection):
                transport = Transport(session=session.session)
            
            # create the client
            soap_client = Client(constants.WebserviceConstants.base_url, wsse=wsse, transport=transport)
            
            print("Standby...testing your access.")    
        
            
            has_access_response = soap_client.service.TestUserAccess()
            
            print(has_access_response)
            
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
