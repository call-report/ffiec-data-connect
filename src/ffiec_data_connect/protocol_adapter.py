"""
FFIEC Protocol Adapter - Phase 1 Implementation

This module provides the abstract base class and concrete implementations for
both SOAP and REST API protocols. The adapter pattern ensures a consistent
interface regardless of the underlying protocol.

Key Features:
- Abstract base class defining common interface
- SOAP adapter wrapping existing functionality
- REST adapter for new FFIEC REST API
- Automatic protocol selection based on credential type
- Transparent data normalization ensuring backward compatibility

Author: FFIEC Data Connect Library
Version: Phase 1 - Protocol Abstraction
"""

import logging
import warnings
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import httpx
import time
import threading

# Keep requests import for SOAP adapter backward compatibility
try:
    import requests
except ImportError:
    requests = None

from .credentials import WebserviceCredentials, OAuth2Credentials
from .data_normalizer import DataNormalizer
from .exceptions import (
    ConnectionError,
    CredentialError,
    FFIECError,
    NoDataError,
    RateLimitError,
    ValidationError
)


logger = logging.getLogger(__name__)


class ProtocolAdapter(ABC):
    """
    Abstract base class for API protocol adapters.
    
    This defines the common interface that both SOAP and REST adapters
    must implement, ensuring consistent behavior regardless of protocol.
    """
    
    @abstractmethod
    def retrieve_reporting_periods(self, series: str) -> List[str]:
        """
        Retrieve available reporting periods for a series.
        
        Args:
            series: Report series (e.g., "call", "ubpr")
            
        Returns:
            List of reporting period strings
        """
        pass
        
    @abstractmethod
    def retrieve_facsimile(self, rssd_id: Union[str, int], reporting_period: str, 
                          series: str) -> bytes:
        """
        Retrieve facsimile data for an institution.
        
        Args:
            rssd_id: Institution RSSD ID
            reporting_period: Reporting period (MM/dd/yyyy)
            series: Report series
            
        Returns:
            Raw facsimile data (XBRL bytes)
        """
        pass
        
    @abstractmethod
    def retrieve_panel_of_reporters(self, reporting_period: str) -> List[Dict]:
        """
        Retrieve panel of reporters for a reporting period.
        
        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            
        Returns:
            List of institution dictionaries
        """
        pass
        
    @abstractmethod
    def retrieve_filers_since_date(self, reporting_period: str, 
                                  since_date: str) -> List[str]:
        """
        Retrieve filers who submitted since a specific date.
        
        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            since_date: Date since which to check submissions (MM/dd/yyyy)
            
        Returns:
            List of RSSD IDs as strings
        """
        pass
        
    @abstractmethod
    def retrieve_filers_submission_datetime(self, reporting_period: str) -> List[Dict]:
        """
        Retrieve filer submission date/time information.
        
        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            
        Returns:
            List of submission info dictionaries
        """
        pass
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Return the protocol name (e.g., 'SOAP', 'REST')."""
        pass


class RESTAdapter(ProtocolAdapter):
    """
    REST API adapter for FFIEC webservice.
    
    This adapter implements the new FFIEC REST API with OAuth2 authentication,
    enhanced rate limiting, and automatic data normalization to maintain
    backward compatibility with SOAP responses.
    """
    
    # FFIEC REST API Configuration
    BASE_URL = "https://ffieccdr.azure-api.us/public"
    
    # Rate limiting: 2500 requests per hour
    DEFAULT_RATE_LIMIT = 2500 / 3600  # requests per second
    
    def __init__(self, credentials: OAuth2Credentials, 
                 rate_limiter: Optional['RateLimiter'] = None,
                 session: Optional[httpx.Client] = None):
        """
        Initialize REST API adapter.
        
        Args:
            credentials: OAuth2 credentials for authentication
            rate_limiter: Optional rate limiter (creates default if None)
            session: Optional httpx client (for compatibility, not used)
        """
        if not isinstance(credentials, OAuth2Credentials):
            raise CredentialError(
                "RESTAdapter requires OAuth2Credentials. "
                "For SOAP API, use SOAPAdapter with WebserviceCredentials."
            )
            
        self.credentials = credentials
        self.rate_limiter = rate_limiter or RateLimiter(
            calls_per_hour=2500,
            calls_per_second=self.DEFAULT_RATE_LIMIT
        )
        
        # Create httpx client (httpx handles non-standard headers better)
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        # Check credentials on initialization
        if self.credentials.is_expired:
            logger.warning("OAuth2 token is expired or expires within 24 hours")
        
        logger.debug("REST client configured with httpx")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                      additional_headers: Optional[Dict] = None) -> Any:
        """
        Make authenticated REST request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (e.g., "RetrieveReportingPeriods")
            params: Query parameters
            additional_headers: Additional headers to include in request
            
        Returns:
            Parsed JSON response
            
        Raises:
            Various FFIEC exceptions based on response status
        """
        # Apply rate limiting
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        # Check token expiration
        if self.credentials.is_expired:
            raise CredentialError(
                "OAuth2 token is expired. Please obtain a new bearer token."
            )
        
        # Prepare request
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self.credentials.get_auth_headers()
        
        # Add any additional headers
        if additional_headers:
            headers.update(additional_headers)
        
        logger.debug(f"Making REST request to {endpoint}")
        logger.debug(f"URL: {url}")
        if params:
            logger.debug(f"Parameters: {params}")
        # Log token info safely
        token_preview = self.credentials.bearer_token[:10] if len(self.credentials.bearer_token) > 10 else "SHORT"
        logger.debug(f"Auth: Bearer token (first 10 chars): {token_preview}...")
        
        try:
            response = self.client.get(
                url,
                headers=headers,
                params=params or {}
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            if response.status_code >= 400:
                logger.debug(f"Error Response Body: {response.text[:500]}")
            
            return self._handle_response(response, endpoint)
            
        except httpx.TimeoutException:
            raise ConnectionError(
                f"Request to {endpoint} timed out after 30 seconds"
            )
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Failed to connect to FFIEC REST API: {e}"
            )
        except httpx.RequestError as e:
            raise FFIECError(f"REST API request failed: {e}")
    
    def _handle_response(self, response: httpx.Response, endpoint: str) -> Any:
        """
        Handle REST API response with proper error mapping.
        
        Args:
            response: Raw HTTP response
            endpoint: API endpoint name for context
            
        Returns:
            Parsed response data
            
        Raises:
            Appropriate FFIEC exceptions based on status code
        """
        logger.debug(f"REST response: {response.status_code} for {endpoint}")
        
        # Handle different status codes
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                raise FFIECError(f"Invalid JSON response from {endpoint}: {e}")
                
        elif response.status_code == 204:
            # No content - return empty response
            return []
            
        elif response.status_code == 400:
            raise ValidationError(
                f"Invalid request parameters for {endpoint}: "
                f"{response.text}"
            )
            
        elif response.status_code == 401:
            raise CredentialError(
                "OAuth2 authentication failed. Token may be expired or invalid."
            )
            
        elif response.status_code == 403:
            # Provide more detailed error message for 403
            error_msg = "Access forbidden (HTTP 403). "
            
            # Check for common OAuth2 issues
            if self.credentials.token_expires:
                from datetime import datetime
                if datetime.now() > self.credentials.token_expires:
                    error_msg += "Bearer token appears to be expired. "
            
            error_msg += "Please verify: 1) Bearer token is valid, 2) Token has correct permissions, 3) Username matches token owner"
            
            raise CredentialError(error_msg)
            
        elif response.status_code == 404:
            raise NoDataError(
                f"No data found for {endpoint} request"
            )
            
        elif response.status_code == 429:
            # Extract retry-after header if available
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    retry_after = 60  # Default to 60 seconds
            else:
                retry_after = 60  # Default if header not present
            
            raise RateLimitError(retry_after=retry_after)
            
        elif response.status_code == 500:
            raise ConnectionError(
                f"FFIEC REST API server error for {endpoint}"
            )
            
        else:
            raise FFIECError(
                f"Unexpected response from {endpoint}: "
                f"{response.status_code} - {response.text}"
            )
    
    def retrieve_reporting_periods(self, series: str) -> List[str]:
        """
        Retrieve available reporting periods via REST API.
        
        Args:
            series: Report series (e.g., "call", "ubpr")
            
        Returns:
            List of reporting period strings (normalized to SOAP format)
        """
        # REST API expects "dataSeries" as a HEADER (not query param)
        # Keep series lowercase as per working curl example
        series_lower = series.lower()
        
        # Add dataSeries as an additional header
        additional_headers = {"dataSeries": series_lower}
        
        try:
            raw_response = self._make_request(
                "RetrieveReportingPeriods", 
                params=None,  # No query parameters
                additional_headers=additional_headers
            )
            
            # Apply data normalization to ensure SOAP compatibility
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveReportingPeriods", "REST"
            )
            
            logger.info(f"Retrieved {len(normalized)} reporting periods for {series}")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to retrieve reporting periods for {series}: {e}")
            raise
    
    def retrieve_facsimile(self, rssd_id: Union[str, int], reporting_period: str, 
                          series: str) -> bytes:
        """
        Retrieve facsimile data via REST API.
        
        Args:
            rssd_id: Institution RSSD ID
            reporting_period: Reporting period (MM/dd/yyyy)
            series: Report series
            
        Returns:
            Raw XBRL data bytes
        """
        params = {
            "rssdId": str(rssd_id),
            "reportingPeriod": reporting_period,
            "series": series
        }
        
        try:
            # The REST API might use POST with JSON payload instead of GET with params
            headers = self.credentials.get_auth_headers()
            # Add dataSeries as header (required for REST API)
            headers["dataSeries"] = series.lower()
            
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()
            
            # Try POST with JSON payload first
            request_data = {
                "rssdId": str(rssd_id),
                "reportingPeriod": reporting_period,
                "series": series.lower()
            }
            
            endpoints_to_try = [
                ("RetrieveFacsimileExt", "POST"),
                ("RetrieveData", "POST"), 
                ("RetrieveFacsimile", "POST"),
                ("RetrieveFacsimileExt", "GET"),
                ("RetrieveData", "GET"),
                ("RetrieveFacsimile", "GET")
            ]
            
            last_error = None
            for endpoint_name, method in endpoints_to_try:
                try:
                    url = f"{self.BASE_URL}/{endpoint_name}"
                    logger.debug(f"Trying REST endpoint: {endpoint_name} with {method}")
                    
                    if method == "POST":
                        response = self.client.post(
                            url,
                            headers=headers,
                            json=request_data
                        )
                    else:
                        response = self.client.get(
                            url,
                            headers=headers,
                            params=params
                        )
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully used endpoint: {endpoint_name} with {method}")
                        return response.content
                    elif response.status_code == 404:
                        # This endpoint doesn't exist, try next
                        continue
                    elif response.status_code == 405:
                        # Method not allowed, try next
                        continue
                    else:
                        # Other error - handle it
                        self._handle_response(response, endpoint_name)
                        
                except Exception as e:
                    last_error = e
                    logger.debug(f"Endpoint {endpoint_name} with {method} failed: {e}")
                    continue
            
            # If we get here, all endpoints failed
            if last_error:
                raise last_error
            else:
                raise ConnectionError(f"No working REST endpoint found for facsimile data")
                
        except Exception as e:
            logger.error(f"Failed to retrieve facsimile for RSSD {rssd_id}: {e}")
            raise
    
    def retrieve_panel_of_reporters(self, reporting_period: str) -> List[Dict]:
        """
        Retrieve panel of reporters via REST API.
        
        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            
        Returns:
            List of institution dictionaries (normalized to SOAP format)
        """
        params = {"reportingPeriod": reporting_period}
        
        try:
            raw_response = self._make_request("RetrievePanelOfReporters", params)
            
            # CRITICAL: Apply normalization to fix format differences
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrievePanelOfReporters", "REST"
            )
            
            logger.info(f"Retrieved {len(normalized)} reporters for {reporting_period}")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to retrieve panel of reporters for {reporting_period}: {e}")
            raise
    
    def retrieve_filers_since_date(self, reporting_period: str, 
                                  since_date: str) -> List[str]:
        """
        Retrieve filers who submitted since date via REST API.
        
        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            since_date: Date since which to check submissions (MM/dd/yyyy)
            
        Returns:
            List of RSSD IDs as strings (normalized to SOAP format)
        """
        params = {
            "reportingPeriod": reporting_period,
            "sinceDate": since_date
        }
        
        try:
            raw_response = self._make_request("RetrieveFilersSinceDate", params)
            
            # Apply normalization (REST returns integers, SOAP expects strings)
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveFilersSinceDate", "REST"
            )
            
            logger.info(f"Retrieved {len(normalized)} filers since {since_date}")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to retrieve filers since {since_date}: {e}")
            raise
    
    def retrieve_filers_submission_datetime(self, reporting_period: str) -> List[Dict]:
        """
        Retrieve filer submission date/time info via REST API.
        
        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            
        Returns:
            List of submission info dictionaries (normalized to SOAP format)
        """
        params = {"reportingPeriod": reporting_period}
        
        try:
            raw_response = self._make_request("RetrieveFilersSubmissionDateTime", params)
            
            # Apply normalization for date/time and ID format consistency
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveFilersSubmissionDateTime", "REST"
            )
            
            logger.info(f"Retrieved submission info for {len(normalized)} filers")
            return normalized
            
        except Exception as e:
            logger.error(f"Failed to retrieve filer submission info: {e}")
            raise
    
    @property
    def protocol_name(self) -> str:
        """Return the protocol name."""
        return "REST"


class SOAPAdapter(ProtocolAdapter):
    """
    SOAP API adapter wrapping existing functionality.
    
    This adapter provides a consistent interface to the existing SOAP-based
    functionality, allowing for transparent protocol selection.
    """
    
    def __init__(self, credentials: WebserviceCredentials, 
                 session: Optional['requests.Session'] = None):
        """
        Initialize SOAP API adapter.
        
        Args:
            credentials: WebserviceCredentials for SOAP authentication
            session: Optional requests session
        """
        if not isinstance(credentials, WebserviceCredentials):
            raise CredentialError(
                "SOAPAdapter requires WebserviceCredentials. "
                "For REST API, use RESTAdapter with OAuth2Credentials."
            )
            
        self.credentials = credentials
        self.session = session
        
        # Issue deprecation warning
        warnings.warn(
            "SOAP API is deprecated and will be removed in v3.0.0. "
            "For better performance and reliability, migrate to REST API using OAuth2Credentials. "
            "See documentation for migration guide.",
            DeprecationWarning,
            stacklevel=3
        )
    
    def retrieve_reporting_periods(self, series: str) -> List[str]:
        """Retrieve reporting periods via SOAP (delegates to existing implementation)."""
        # Import here to avoid circular imports
        from . import methods
        
        # Use existing implementation
        return methods.collect_reporting_periods(
            self.session, self.credentials, series=series
        )
    
    def retrieve_facsimile(self, rssd_id: Union[str, int], reporting_period: str, 
                          series: str) -> bytes:
        """Retrieve facsimile data via SOAP (delegates to existing implementation)."""
        from . import methods
        
        # Use existing implementation
        return methods.collect_data(
            self.session, self.credentials, reporting_period, rssd_id, series=series
        )
    
    def retrieve_panel_of_reporters(self, reporting_period: str) -> List[Dict]:
        """Retrieve panel of reporters via SOAP (delegates to existing implementation)."""
        from . import methods
        
        # Use existing implementation
        return methods.collect_filers_on_reporting_period(
            self.session, self.credentials, reporting_period
        )
    
    def retrieve_filers_since_date(self, reporting_period: str, 
                                  since_date: str) -> List[str]:
        """Retrieve filers since date via SOAP (delegates to existing implementation)."""
        from . import methods
        
        # Use existing implementation
        return methods.collect_filers_since_date(
            self.session, self.credentials, reporting_period, since_date
        )
    
    def retrieve_filers_submission_datetime(self, reporting_period: str) -> List[Dict]:
        """Retrieve filer submission info via SOAP (delegates to existing implementation)."""
        from . import methods
        
        # Use existing implementation
        return methods.collect_filers_submission_date_time(
            self.session, self.credentials, reporting_period
        )
    
    @property
    def protocol_name(self) -> str:
        """Return the protocol name."""
        return "SOAP"


class RateLimiter:
    """
    Enhanced rate limiter for REST API with both per-second and per-hour limits.
    
    The FFIEC REST API has a limit of 2500 requests per hour. This rate limiter
    enforces both per-second smoothing and hourly quota management.
    """
    
    def __init__(self, calls_per_hour: int = 2500, calls_per_second: float = 0.69):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_hour: Maximum calls per hour (default 2500 for FFIEC REST API)
            calls_per_second: Maximum calls per second for smoothing
        """
        self.calls_per_hour = calls_per_hour
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        
        self.last_call = 0.0
        self.call_history = []  # Timestamps of recent calls
        self.lock = threading.Lock()
        
        logger.debug(f"Rate limiter initialized: {calls_per_hour}/hour, {calls_per_second}/sec")
    
    def wait_if_needed(self) -> None:
        """
        Wait if needed to respect both per-second and per-hour rate limits.
        
        This method blocks until it's safe to make the next request.
        """
        with self.lock:
            now = time.time()
            
            # Clean old calls (older than 1 hour)
            hour_ago = now - 3600
            self.call_history = [timestamp for timestamp in self.call_history 
                               if timestamp > hour_ago]
            
            # Check hourly limit
            if len(self.call_history) >= self.calls_per_hour:
                # Need to wait until oldest call is more than 1 hour ago
                oldest_call = self.call_history[0]
                wait_time = oldest_call + 3600 - now
                
                if wait_time > 0:
                    logger.warning(f"Hourly rate limit reached. Waiting {wait_time:.1f} seconds")
                    time.sleep(wait_time)
                    now = time.time()
            
            # Check per-second limit
            time_since_last = now - self.last_call
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                time.sleep(wait_time)
                now = time.time()
            
            # Record this call
            self.last_call = now
            self.call_history.append(now)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.
        
        Returns:
            Dictionary with current rate limiting status
        """
        with self.lock:
            now = time.time()
            hour_ago = now - 3600
            recent_calls = [t for t in self.call_history if t > hour_ago]
            
            return {
                "calls_this_hour": len(recent_calls),
                "hourly_limit": self.calls_per_hour,
                "hourly_remaining": self.calls_per_hour - len(recent_calls),
                "per_second_limit": self.calls_per_second,
                "last_call_seconds_ago": now - self.last_call if self.last_call else None
            }


def create_protocol_adapter(credentials: Union[WebserviceCredentials, OAuth2Credentials],
                          session: Optional['requests.Session'] = None) -> ProtocolAdapter:
    """
    Factory function to create appropriate protocol adapter based on credential type.
    
    This is the main entry point for automatic protocol selection. Based on the
    credential type provided, it returns either a SOAP or REST adapter.
    
    Args:
        credentials: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
        session: Optional requests session
        
    Returns:
        Appropriate protocol adapter
        
    Raises:
        CredentialError: If credential type is not supported
    """
    if isinstance(credentials, OAuth2Credentials):
        logger.info("Creating REST adapter for OAuth2 credentials")
        return RESTAdapter(credentials, session=session)
        
    elif isinstance(credentials, WebserviceCredentials):
        logger.info("Creating SOAP adapter for WebserviceCredentials")
        return SOAPAdapter(credentials, session=session)
        
    else:
        raise CredentialError(
            f"Unsupported credential type: {type(credentials)}. "
            "Use WebserviceCredentials for SOAP or OAuth2Credentials for REST."
        )