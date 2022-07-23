"""Wrapper to establish requests.Session and set proxy server values if needed

`An instance of this class may be substituted for an instance requests.Session class.`
"""

import requests
from enum import Enum


class ProxyProtocol(Enum):
    """Enumerated values that represent the proxy protocol options

    Args:
        Enum (ProxyProtocol): Enumerated value for HTTP or HTTPS
    """
    
    HTTP = 0
    HTTPS = 1

class FFIECConnection(object):
    """Creates a FFIECConnection object, which may include proxy server connection parameters
    """
    
    def __init__(self) -> None:
        """Initializes the Https Connection to be utilized
        to connect to the FFIEC website
        
        Args:
            None
        
        
        """
        
        self.use_proxy = False
        self.proxy_host = None
        self.proxy_port = None
        self.proxy_password = None
        self.proxy_user_name = None
        self.proxy_protocol = None
        
        self._generate_session()
        
        return
    
    @property
    def session(self) -> requests.Session:
        """Returns the requests.Session object
        * Note that this property may be utilized for methods in the `methods` module.
        
        `This session property is automatically generated when the FFIECConnection object is created.`
        
        Returns:
            requests.Session: the requests.Session object
        
        """
        return self._session
    
    @session.setter
    def session(self, session: requests.Session) -> None:
        """Set the requests.Session object
        
        Args:
            session (requests.Session): the requests.Session object
        """
        self._session = session
        return
        
    @property
    def proxy_host(self) -> str:
        """Returns the hostname of the proxy server
        
        Returns:
            str: The hostname of the proxy server
        
        """
        return self._proxy_host
        
    @proxy_host.setter
    def proxy_host(self, host: str) -> None:
        """Set the optional proxy hostname

        Args:
            host (str): the host name of the proxy server
        """
        
        self._generate_session()
        
        self._proxy_host = host
        pass
    
    @property
    def proxy_protocol(self) -> int:
        """Returns the protocol of the proxy server
        
        Returns:
            int: the protocol of the proxy server
        
        """
        return self._proxy_protocol
    
    @proxy_protocol.setter
    def proxy_protocol(self, protocol: ProxyProtocol) -> None:
        """Set the optional proxy protocol

        Args:
            protocol (str): the protocol of the proxy server
        """
        self._generate_session()
        
        self._proxy_protocol = protocol
        pass
    
    @property
    def proxy_port(self) -> int:
        """Get the optional proxy port

        Returns:
            int: the proxy port
        """
        return self._proxy_port
    
    @proxy_port.setter
    def proxy_port(self, port: int) -> None:
        """Set the optional proxy port

        Args:
            port (int): the port of the proxy server
        """
        
        self._generate_session()
        
        self._proxy_port = port
        pass
    
    @property
    def proxy_user_name(self) -> str:
        """Get the optional proxy username
        
        Returns:
            str: the proxy username
        
        """
        
        self._generate_session()
        
        return self._proxy_user_name
    
    @proxy_user_name.setter
    def proxy_user_name(self, username: str) -> None:
        """Set the optional proxy username

        Args:
            username (str): the username of the proxy server
        """
        
        self._generate_session()
        
        self._proxy_user_name = username
        pass
    
    @property
    def proxy_password(self) -> str:
        """Get the optional proxy password
        
        Returns:
            str: the password of the proxy server
        
        """
        return self._proxy_password
    
    @proxy_password.setter
    def proxy_password(self, password: str) -> None:
        """Set the optional proxy password

        Args:
            password (str): the password of the proxy server
        """
        
        self._generate_session()
        
        self._proxy_password = password
        pass
    
    @property
    def use_proxy(self) -> bool:
        """Get the optional proxy flag
        
        Returns:
            bool: the proxy flag (True if proxy is used, False if not)
        
        """
        return self._use_proxy
    
    @use_proxy.setter
    def use_proxy(self, use_proxy_opt: bool) -> None:
        """Set the optional proxy flag
        If set to True, the proxy server will be used

        Args:
            useProxy (bool): the flag to use the proxy server
        """
        
        # # if we are setting the proxy to true, check that we have, at minimum, a host name, port, and protocol
        # if use_proxy_opt:
        #     if self.proxy_host is None or self.proxy_port is None or self.proxy_protocol is None:
        #         raise ValueError("Proxy host, port, and protocol must be set before using the proxy")
        
        #     else:
        #         self._use_proxy = use_proxy_opt
                
        #         self._generate_session()
        # else:
        #     self._generate_session()

        self._use_proxy = use_proxy_opt
        
        self._generate_session()
            
        return
    
   
    def _generate_session(self) -> requests.Session:
        """Internal class method to generate a requests session object

        """
        
        # create a requests session
        session = requests.Session()
        
        # are we using a proxy?
        if self.use_proxy:
            
            # check that we have a hostname, port, and protocol. If not, raise an error
            if self.proxy_host is None or self.proxy_port is None or self.proxy_protocol is None:
                raise()
            
            
            # if we are using a proxy, set the proxy host and port
            session.proxies = {self.proxy_protocol.name: 'http://' + self.proxy_host + ':' + str(self.proxy_port)}
            # if we have a username and password, set the proxy username and password
            if self.proxy_user_name is not None and self.proxy_password is not None:
                session.proxies['http']['proxy_auth'] = (self._proxy_user_name, self.proxy_password)
        
         # set the session to self.connection
        self.session = session

        return
    
   
    def test_connection(self, url: str = "https://google.com") -> bool:
        """Tests a connection, using the proxy server if one is not set
        
        Note: This method tests if a web page on the public internet (not the FFIEC webservice) 
        is accessible using this library, through the proxy server.
        
        We do not yet test access to the Webservice, because a user name and password
        is needed to access the Webservice, which is outside the scope of this module.
        
        An alternative web site may be selected in lieu of google.com,
        using the url parameter.
        
        """
        
        # can we return a HTTP 200 from google.com, or the url specified??
        
        if url is None:
            url = "https://google.com"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return True
        else:
            print("Unable to access test site via proxy. Error: " + str(response.status_code))
            return False


    def __str__(self) -> str:
        
        """String representation of the HttpsConnection object
        
        Returns:
            str: the string representation of the HttpsConnection object
        
        """
        return f"""
        HttpsConnection object properties:
        
        Https connection session is {'active' if self.session is not None else 'inactive'}
        
        
        proxy hostname = {self.proxy_host}
        proxy port = {self.proxy_port}
        proxy protocol = {self.proxy_protocol}
        is the proxy active? = {self.use_proxy}
        proxy username = {self.proxy_user_name}
        is proxy password set? = {self.proxy_password is not None}
        
        """
        
    

    def __repr__(self) -> str:
        return self.__str__()