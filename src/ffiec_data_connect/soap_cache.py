"""
SOAP client caching system for FFIEC Data Connect.

This module provides thread-safe caching of SOAP clients to prevent
expensive recreation and improve performance.
"""

import hashlib
import threading
import weakref
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Union

from zeep import Client, Settings
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken

from ffiec_data_connect import constants
from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.exceptions import ConnectionError, raise_exception
from ffiec_data_connect.ffiec_connection import FFIECConnection


@dataclass(frozen=True)
class SOAPClientConfig:
    """Immutable configuration for SOAP client caching."""

    wsdl_url: str
    username: str
    # Derived cache key identifier (not the actual credentials)
    credential_key: str
    proxy_config: Optional[str] = None
    timeout: int = 30

    @classmethod
    def from_credentials_and_session(
        cls,
        credentials: WebserviceCredentials,
        session: Union[FFIECConnection, Any],
        wsdl_url: Optional[str] = None,
    ) -> "SOAPClientConfig":
        """Create config from credentials and session."""
        if wsdl_url is None:
            wsdl_url = constants.WebserviceConstants.base_url

        # Generate a unique identifier for cache key using PBKDF2
        # This is a proper key derivation function designed for this purpose
        # We use the username as salt to ensure different users get different keys
        salt = f"ffiec-{credentials.username}".encode()
        # Derive a key from credentials for cache identification
        # Using 1000 iterations which is fast enough for caching but secure
        credential_key = hashlib.pbkdf2_hmac(
            "sha256",
            credentials.password.encode(),  # This is the data to derive from
            salt,  # Salt includes username for uniqueness
            1000,  # Number of iterations
            dklen=16,  # Output 16 bytes (32 hex chars)
        ).hex()

        # Extract proxy configuration if available
        proxy_config = None
        if hasattr(session, "use_proxy") and session.use_proxy:
            proxy_config = (
                f"{session.proxy_protocol}://{session.proxy_host}:{session.proxy_port}"
            )

        return cls(
            wsdl_url=wsdl_url,
            username=credentials.username,
            credential_key=credential_key,  # Using PBKDF2-derived key
            proxy_config=proxy_config,
        )

    def cache_key(self) -> str:
        """Generate cache key for this configuration."""
        # Use hash of all config values for cache key
        config_str = str(asdict(self))
        return hashlib.md5(config_str.encode(), usedforsecurity=False).hexdigest()


class SOAPClientCache:
    """Thread-safe cache for SOAP clients."""

    def __init__(self, max_size: int = 10):
        """Initialize cache with maximum size."""
        self._cache: Dict[str, Client] = {}
        self._access_order: Dict[str, int] = {}
        self._access_counter = 0
        self._max_size = max_size
        self._lock = threading.RLock()

        # Track cache for cleanup
        self._instances: weakref.WeakSet["SOAPClientCache"] = weakref.WeakSet()
        self._instances.add(self)

    def get_client(
        self,
        config: SOAPClientConfig,
        credentials: WebserviceCredentials,
        session: Union[FFIECConnection, Any],
    ) -> Client:
        """Get or create SOAP client with caching."""
        cache_key = config.cache_key()

        with self._lock:
            # Check if client exists in cache
            if cache_key in self._cache:
                # Update access order for LRU
                self._access_counter += 1
                self._access_order[cache_key] = self._access_counter
                return self._cache[cache_key]

            # Create new client
            try:
                client = self._create_soap_client(config, credentials, session)

                # Add to cache (with LRU eviction if needed)
                self._add_to_cache(cache_key, client)

                return client

            except Exception as e:
                raise_exception(
                    ConnectionError,
                    f"Failed to create SOAP client: {str(e)}",
                    f"Failed to create SOAP client for {config.wsdl_url}: {str(e)}",
                    url=config.wsdl_url,
                )
                # This should never be reached due to raise_exception throwing an exception
                raise  # Add explicit raise to satisfy type checker

    def _create_soap_client(
        self,
        config: SOAPClientConfig,
        credentials: WebserviceCredentials,
        session: Union[FFIECConnection, Any],
    ) -> Client:
        """Create a new SOAP client."""
        # Create WSSE token
        wsse = UsernameToken(credentials.username, credentials.password)  # type: ignore[no-untyped-call]

        # Create transport with session
        transport = None
        if hasattr(session, "session"):
            # FFIECConnection object
            transport = Transport(session=session.session)  # type: ignore[no-untyped-call]
        else:
            # Direct requests.Session
            transport = Transport(session=session)  # type: ignore[no-untyped-call]

        # Create settings for better performance
        settings = Settings(
            strict=False,  # Allow minor WSDL issues
            raw_response=False,
            force_https=True,
        )

        # Create client
        return Client(  # type: ignore[no-untyped-call]
            wsdl=config.wsdl_url, wsse=wsse, transport=transport, settings=settings
        )

    def _add_to_cache(self, key: str, client: Client) -> None:
        """Add client to cache with LRU eviction."""
        # If at max size, remove least recently used
        if len(self._cache) >= self._max_size:
            self._evict_lru()

        self._access_counter += 1
        self._cache[key] = client
        self._access_order[key] = self._access_counter

    def _evict_lru(self) -> None:
        """Evict least recently used client."""
        if not self._cache:
            return

        # Find LRU key
        lru_key = min(self._access_order.keys(), key=lambda k: self._access_order[k])

        # Clean up client if possible
        try:
            client = self._cache[lru_key]
            if hasattr(client.transport, "session") and hasattr(
                client.transport.session, "close"
            ):
                client.transport.session.close()
        except Exception:
            pass  # Ignore cleanup errors

        # Remove from cache
        del self._cache[lru_key]
        del self._access_order[lru_key]

    def clear(self) -> None:
        """Clear all cached clients."""
        with self._lock:
            # Clean up all clients
            for client in self._cache.values():
                try:
                    if hasattr(client.transport, "session") and hasattr(
                        client.transport.session, "close"
                    ):
                        client.transport.session.close()
                except Exception:
                    pass

            self._cache.clear()
            self._access_order.clear()
            self._access_counter = 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hit_ratio": getattr(self, "_hits", 0)
                / max(getattr(self, "_requests", 1), 1),
                "keys": list(self._cache.keys()),
            }

    @classmethod
    def cleanup_all(cls) -> None:
        """Clean up all cache instances."""
        for cache in list(cls._instances):
            try:
                cache.clear()
            except Exception:
                pass


# Global cache instance
_global_soap_cache = SOAPClientCache(max_size=20)


def get_soap_client(
    credentials: WebserviceCredentials,
    session: Union[FFIECConnection, Any],
    wsdl_url: Optional[str] = None,
) -> Client:
    """Get cached SOAP client for the given configuration.

    This function provides the main interface for getting cached SOAP clients.

    Args:
        credentials: FFIEC webservice credentials
        session: Session object (FFIECConnection or requests.Session)
        wsdl_url: Optional WSDL URL (defaults to FFIEC webservice)

    Returns:
        Cached or newly created zeep Client instance
    """
    config = SOAPClientConfig.from_credentials_and_session(
        credentials, session, wsdl_url
    )

    return _global_soap_cache.get_client(config, credentials, session)


def clear_soap_cache() -> None:
    """Clear the global SOAP client cache."""
    _global_soap_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about the SOAP client cache."""
    return _global_soap_cache.stats()
