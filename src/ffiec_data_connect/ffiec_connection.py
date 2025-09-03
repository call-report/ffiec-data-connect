"""Wrapper to establish requests.Session and set proxy server values if needed

`An instance of this class may be substituted for an instance requests.Session class.`
"""

import threading
import weakref
from enum import Enum
from typing import Any, Optional, Type

import requests

from ffiec_data_connect.exceptions import SessionError, raise_exception


class ProxyProtocol(Enum):
    """Enumerated values that represent the proxy protocol options

    Args:
        Enum (ProxyProtocol): Enumerated value for HTTP or HTTPS
    """

    HTTP = 0
    HTTPS = 1


class FFIECConnection(object):
    """Thread-safe FFIECConnection with proper resource management.

    This class provides a thread-safe connection to the FFIEC webservice
    with optional proxy support and automatic resource cleanup.
    """

    # Class-level registry for tracking instances (for cleanup)
    _instances: "weakref.WeakSet[FFIECConnection]" = weakref.WeakSet()

    def __init__(self) -> None:
        """Initializes the Https Connection to be utilized
        to connect to the FFIEC website with thread safety.

        Args:
            None
        """
        # Thread safety lock
        self._lock = threading.RLock()

        # Initialize session as None - will be created on first access
        self._session: Optional[requests.Session] = None

        # Proxy configuration (thread-safe via properties)
        self._use_proxy = False
        self._proxy_host: Optional[str] = None
        self._proxy_port: Optional[int] = None
        self._proxy_password: Optional[str] = None
        self._proxy_user_name: Optional[str] = None
        self._proxy_protocol: Optional[ProxyProtocol] = None

        # Track configuration state to avoid unnecessary regeneration
        self._config_hash: Optional[int] = None

        # Register instance for cleanup
        FFIECConnection._instances.add(self)

        return

    @property
    def session(self) -> requests.Session:
        """Returns the requests.Session object (lazy-loaded and thread-safe).

        * Note that this property may be utilized for methods in the `methods` module.
        * The session is created on first access and reused thereafter.
        * Thread-safe: Multiple threads can safely access this property.

        Returns:
            requests.Session: the requests.Session object
        """
        with self._lock:
            if self._session is None:
                self._generate_session()
            assert (
                self._session is not None
            )  # _generate_session should always create a session
            return self._session

    @session.setter
    def session(self, session: requests.Session) -> None:
        """Set the requests.Session object (thread-safe).

        Args:
            session (requests.Session): the requests.Session object
        """
        with self._lock:
            # Close old session if it exists
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass  # Ignore errors during cleanup
            self._session = session
        return

    @property
    def proxy_host(self) -> Optional[str]:
        """Returns the hostname of the proxy server

        Returns:
            str: The hostname of the proxy server

        """
        return self._proxy_host

    @proxy_host.setter
    def proxy_host(self, host: str) -> None:
        """Set the optional proxy hostname (thread-safe).

        Args:
            host (str): the host name of the proxy server
        """
        with self._lock:
            self._proxy_host = host
            # Mark configuration as changed
            self._config_hash = None

    @property
    def proxy_protocol(self) -> Optional[ProxyProtocol]:
        """Returns the protocol of the proxy server

        Returns:
            int: the protocol of the proxy server

        """
        return self._proxy_protocol

    @proxy_protocol.setter
    def proxy_protocol(self, protocol: ProxyProtocol) -> None:
        """Set the optional proxy protocol (thread-safe).

        Args:
            protocol (ProxyProtocol): the protocol of the proxy server
        """
        with self._lock:
            self._proxy_protocol = protocol
            self._config_hash = None

    @property
    def proxy_port(self) -> Optional[int]:
        """Get the optional proxy port

        Returns:
            int: the proxy port
        """
        return self._proxy_port

    @proxy_port.setter
    def proxy_port(self, port: int) -> None:
        """Set the optional proxy port (thread-safe).

        Args:
            port (int): the port of the proxy server
        """
        with self._lock:
            self._proxy_port = port
            self._config_hash = None

    @property
    def proxy_user_name(self) -> Optional[str]:
        """Get the optional proxy username

        Returns:
            str: the proxy username

        """
        return self._proxy_user_name

    @proxy_user_name.setter
    def proxy_user_name(self, username: str) -> None:
        """Set the optional proxy username (thread-safe).

        Args:
            username (str): the username of the proxy server
        """
        with self._lock:
            self._proxy_user_name = username
            self._config_hash = None

    @property
    def proxy_password(self) -> Optional[str]:
        """Get the optional proxy password

        Returns:
            str: the password of the proxy server

        """
        return self._proxy_password

    @proxy_password.setter
    def proxy_password(self, password: str) -> None:
        """Set the optional proxy password (thread-safe).

        Args:
            password (str): the password of the proxy server
        """
        with self._lock:
            self._proxy_password = password
            self._config_hash = None

    @property
    def use_proxy(self) -> bool:
        """Get the optional proxy flag

        Returns:
            bool: the proxy flag (True if proxy is used, False if not)

        """
        return self._use_proxy

    @use_proxy.setter
    def use_proxy(self, use_proxy_opt: bool) -> None:
        """Set the optional proxy flag (thread-safe).
        If set to True, the proxy server will be used

        Args:
            use_proxy_opt (bool): the flag to use the proxy server
        """
        with self._lock:
            if use_proxy_opt and (
                self._proxy_host is None
                or self._proxy_port is None
                or self._proxy_protocol is None
            ):
                raise_exception(
                    SessionError,
                    "Cannot enable proxy without complete configuration",
                    "Cannot enable proxy without complete configuration. "
                    "Please set proxy_host, proxy_port, and proxy_protocol first.",
                    session_state="proxy_incomplete",
                )
            self._use_proxy = use_proxy_opt
            self._config_hash = None

    def _generate_session(self) -> None:
        """Internal class method to generate a requests session object (thread-safe).

        This method is thread-safe and properly cleans up old sessions to prevent memory leaks.
        """
        # Check if configuration has changed
        current_config = self._get_config_hash()
        if self._session is not None and self._config_hash == current_config:
            return  # No need to regenerate

        # Close old session if it exists (prevent memory leak)
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass  # Ignore errors during cleanup

        # create a new requests session
        session = requests.Session()

        # are we using a proxy?
        if self._use_proxy:
            # check that we have a hostname, port, and protocol. If not, raise an error
            if (
                self.proxy_host is None
                or self.proxy_port is None
                or self.proxy_protocol is None
            ):
                missing = []
                if self.proxy_host is None:
                    missing.append("proxy_host")
                if self.proxy_port is None:
                    missing.append("proxy_port")
                if self.proxy_protocol is None:
                    missing.append("proxy_protocol")

                raise_exception(
                    SessionError,
                    f"Proxy is enabled but configuration is incomplete. Missing: {', '.join(missing)}",
                    f"Proxy is enabled but configuration is incomplete. Missing: {', '.join(missing)}. "
                    "Please set all proxy parameters before enabling proxy.",
                    session_state="proxy_incomplete",
                )

            # if we are using a proxy, set the proxy host and port
            assert (
                self.proxy_host is not None and self.proxy_port is not None
            )  # Should be validated earlier
            proxy_url = "http://" + self.proxy_host + ":" + str(self.proxy_port)

            # if we have a username and password, include them in the URL
            if self.proxy_user_name is not None and self.proxy_password is not None:
                proxy_url = f"http://{self._proxy_user_name}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"

            session.proxies = {"http": proxy_url, "https": proxy_url}

        # set the session and update config hash
        self._session = session
        self._config_hash = current_config

    def _get_config_hash(self) -> int:
        """Generate a hash of the current configuration for change detection."""
        config = (
            self._use_proxy,
            self._proxy_host,
            self._proxy_port,
            self._proxy_protocol.value if self._proxy_protocol else None,
            self._proxy_user_name is not None,  # Don't include actual password in hash
            self._proxy_password is not None,
        )
        return hash(config)

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
            print(
                "Unable to access test site via proxy. Error: "
                + str(response.status_code)
            )
            return False

    def __str__(self) -> str:
        """String representation of the HttpsConnection object - masks sensitive data for security.

        Returns:
            str: the string representation of the HttpsConnection object
        """
        # Mask sensitive proxy information
        masked_host = self._mask_host(self.proxy_host) if self.proxy_host else "None"
        masked_username = (
            self._mask_string(self.proxy_user_name) if self.proxy_user_name else "None"
        )

        return (
            f"FFIECConnection(\n"
            f"  session_status={'active' if self._session is not None else 'inactive'},\n"
            f"  proxy_enabled={self.use_proxy},\n"
            f"  proxy_host='{masked_host}',\n"
            f"  proxy_port={self.proxy_port},\n"
            f"  proxy_protocol={self.proxy_protocol.name if self.proxy_protocol else 'None'},\n"
            f"  proxy_username='{masked_username}',\n"
            f"  proxy_password_set={self.proxy_password is not None}\n"
            f")"
        )

    def _mask_host(self, host: Optional[str]) -> str:
        """Mask hostname, showing only domain."""
        if not host:
            return "***"
        parts = host.split(".")
        if len(parts) <= 2:
            return "***." + parts[-1] if len(parts) > 1 else "***"
        return "***." + ".".join(parts[-2:])

    def _mask_string(self, value: Optional[str]) -> str:
        """Mask sensitive string data."""
        if not value:
            return "***"
        if len(value) <= 2:
            return "*" * len(value)
        return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"

    def __repr__(self) -> str:
        return self.__str__()

    def close(self) -> None:
        """Close the session and free resources.

        This method should be called when the connection is no longer needed
        to ensure proper cleanup of network resources.
        """
        with self._lock:
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass  # Ignore errors during cleanup
                self._session = None
                self._config_hash = None

    def __del__(self) -> None:
        """Cleanup when object is garbage collected."""
        self.close()

    def __enter__(self) -> "FFIECConnection":
        """Context manager entry - returns self."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit - ensures cleanup."""
        self.close()
        return None

    @classmethod
    def cleanup_all(cls) -> None:
        """Class method to cleanup all registered instances.

        This can be useful for cleanup in testing or shutdown scenarios.
        """
        for instance in list(cls._instances):
            try:
                instance.close()
            except Exception:
                pass  # Ignore errors during cleanup
