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
import threading
import time
import warnings
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import httpx

# Import Pydantic models for response validation
from pydantic import ValidationError as PydanticValidationError

# Keep requests import for SOAP adapter backward compatibility
try:
    import requests
except ImportError:
    requests = None  # type: ignore

from .credentials import OAuth2Credentials, WebserviceCredentials
from .data_normalizer import DataNormalizer
from .exceptions import (
    ConnectionError,
    CredentialError,
    FFIECError,
    NoDataError,
    RateLimitError,
    ValidationError,
)
from .models import (
    InstitutionsResponse,
    ReportingPeriodsResponse,
    RSSDIDsResponse,
    SubmissionsResponse,
    UBPRReportingPeriodsResponse,
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
            List of reporting period strings (validated against schema)
        """
        pass

    @abstractmethod
    def retrieve_facsimile(
        self, rssd_id: Union[str, int], reporting_period: str, series: str
    ) -> bytes:
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
    def retrieve_panel_of_reporters(
        self, reporting_period: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve panel of reporters for a reporting period.

        Args:
            reporting_period: Reporting period (MM/dd/yyyy)

        Returns:
            List of institution dictionaries
        """
        pass

    @abstractmethod
    def retrieve_filers_since_date(
        self, reporting_period: str, since_date: str
    ) -> List[str]:
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
    def retrieve_filers_submission_datetime(
        self, reporting_period: str, since_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve filer submission date/time information.

        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            since_date: Optional date to filter submissions since (MM/dd/yyyy)

        Returns:
            List of submission info dictionaries
        """
        pass

    @abstractmethod
    def retrieve_ubpr_reporting_periods(self) -> List[str]:
        """
        Retrieve UBPR reporting periods.

        Returns:
            List of available UBPR reporting periods
        """
        pass

    @abstractmethod
    def retrieve_ubpr_xbrl_facsimile(
        self, rssd_id: Union[str, int], reporting_period: str
    ) -> bytes:
        """
        Retrieve UBPR XBRL facsimile data.

        Args:
            rssd_id: Institution RSSD ID
            reporting_period: Reporting period

        Returns:
            Raw UBPR XBRL data bytes
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

    def __init__(
        self,
        credentials: OAuth2Credentials,
        rate_limiter: Optional["RateLimiter"] = None,
        session: Optional[httpx.Client] = None,
    ):
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
            calls_per_hour=2500, calls_per_second=self.DEFAULT_RATE_LIMIT
        )

        # Create httpx client (httpx handles non-standard headers better)
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

        # Check credentials on initialization
        if self.credentials.is_expired:
            logger.warning("OAuth2 token is expired or expires within 24 hours")

        logger.debug("REST client configured with httpx")

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Make authenticated REST request with rate limiting and error handling.

        CRITICAL: FFIEC REST API passes ALL parameters as headers, not query params!

        Args:
            endpoint: API endpoint (e.g., "RetrieveReportingPeriods")
            params: Parameters to pass as HEADERS (not query params)
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

        # CRITICAL: For FFIEC REST API, ALL parameters are passed as headers!
        if params:
            headers.update(params)

        # Add any additional headers
        if additional_headers:
            headers.update(additional_headers)

        logger.debug(f"Making REST request to {endpoint}")
        logger.debug(f"URL: {url}")
        logger.debug(
            f"Headers (excluding auth): {[k for k in headers.keys() if k != 'Authentication']}"
        )
        # Log token info safely
        token_preview = (
            self.credentials.bearer_token[:10]
            if len(self.credentials.bearer_token) > 10
            else "SHORT"
        )
        logger.debug(f"Auth: Bearer token (first 10 chars): {token_preview}...")

        try:
            # No query params - everything is in headers!
            response = self.client.get(url, headers=headers)

            logger.debug(f"Response Status: {response.status_code}")
            if response.status_code >= 400:
                logger.debug(f"Error Response Body: {response.text[:500]}")

            return self._handle_response(response, endpoint)

        except httpx.TimeoutException:
            raise ConnectionError(f"Request to {endpoint} timed out after 30 seconds")
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to FFIEC REST API: {e}")
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
                field=endpoint,
                value="request_parameters",
                expected=f"Valid parameters for {endpoint}. Error: {response.text}",
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
            raise NoDataError(f"No data found for {endpoint} request")

        elif response.status_code == 429:
            # Extract retry-after header if available
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    retry_after = 60  # Default to 60 seconds
            else:
                retry_after = 60  # Default if header not present

            raise RateLimitError(retry_after=retry_after)

        elif response.status_code == 500:
            raise ConnectionError(f"FFIEC REST API server error for {endpoint}")

        else:
            raise FFIECError(
                f"Unexpected response from {endpoint}: "
                f"{response.status_code} - {response.text}"
            )

    def _validate_response(self, data: Any, model_class: Any, endpoint: str) -> Any:
        """
        Validate response data using Pydantic models.

        Args:
            data: Raw response data
            model_class: Pydantic model class for validation
            endpoint: API endpoint name for error context

        Returns:
            Validated data (unwrapped from RootModel if needed)

        Raises:
            ValidationError: If data doesn't match schema
        """
        try:
            # First validate the data
            validated = model_class(data)

            # Check if this is a RootModel by looking for the root attribute on the instance
            if hasattr(validated, "root"):
                # RootModel - return the root data
                root_data = validated.root

                # Handle nested RootModels (e.g., List[ReportingPeriod] where ReportingPeriod is also RootModel)
                if (
                    isinstance(root_data, list)
                    and root_data
                    and hasattr(root_data[0], "root")
                ):
                    # Extract the root values from nested RootModel objects
                    return [item.root for item in root_data]
                else:
                    return root_data
            else:
                # Regular model - return the validated instance
                return validated

        except PydanticValidationError as e:
            logger.error(f"Schema validation failed for {endpoint}: {e}")
            raise ValidationError(
                field=endpoint,
                value=str(data)[:200] + "..." if len(str(data)) > 200 else str(data),
                expected=f"Valid API response schema for {endpoint}. Schema error: {e}",
            )

    def retrieve_reporting_periods(self, series: str) -> List[str]:
        """
        Retrieve available reporting periods via REST API.

        Args:
            series: Report series (e.g., "call", "ubpr")

        Returns:
            List of reporting period strings (normalized to SOAP format)
        """
        # REST API expects "dataSeries" as a HEADER
        # Use "Call" or "UBPR" (capitalized) per PDF documentation
        series_mapped = "Call" if series.lower() == "call" else "UBPR"

        # Add dataSeries as an additional header
        additional_headers = {"dataSeries": series_mapped}

        try:
            raw_response = self._make_request(
                "RetrieveReportingPeriods",
                params=None,  # No query parameters
                additional_headers=additional_headers,
            )

            # Apply data normalization to ensure SOAP compatibility
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveReportingPeriods", "REST"
            )

            # Validate response against schema
            if series.lower() == "call":
                validated = self._validate_response(
                    normalized, ReportingPeriodsResponse, "RetrieveReportingPeriods"
                )
            else:
                validated = self._validate_response(
                    normalized,
                    UBPRReportingPeriodsResponse,
                    "RetrieveUBPRReportingPeriods",
                )

            logger.info(
                f"Retrieved and validated {len(validated)} reporting periods for {series}"
            )
            return validated  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to retrieve reporting periods for {series}: {e}")
            raise

    def retrieve_facsimile(
        self, rssd_id: Union[str, int], reporting_period: str, series: str
    ) -> bytes:
        """
        Retrieve facsimile data via REST API.

        Args:
            rssd_id: Institution RSSD ID
            reporting_period: Reporting period (MM/dd/yyyy)
            series: Report series

        Returns:
            Raw XBRL data bytes
        """
        try:
            # UBPR data requires different endpoint - route to specialized method
            if series.lower() == "ubpr":
                return self.retrieve_ubpr_xbrl_facsimile(rssd_id, reporting_period)

            # Call Report data uses RetrieveFacsimile endpoint
            series_mapped = "Call" if series.lower() == "call" else "UBPR"

            # ALL parameters are passed as headers per PDF!
            headers = self.credentials.get_auth_headers()
            headers.update(
                {
                    "dataSeries": series_mapped,
                    "fiIdType": "ID_RSSD",  # Note: lowercase 'd' in fiId per PDF
                    "fiId": str(rssd_id),
                    "reportingPeriodEndDate": reporting_period,
                    "facsimileFormat": "XBRL",
                }
            )

            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            url = f"{self.BASE_URL}/RetrieveFacsimile"

            logger.debug(
                f"Calling RetrieveFacsimile with headers: {[k for k in headers.keys() if k != 'Authentication']}"
            )

            response = self.client.get(url, headers=headers)

            if response.status_code == 200:
                logger.info(f"Successfully retrieved facsimile for RSSD {rssd_id}")

                # Check if response is JSON (contains base64-encoded XBRL)
                content_type = response.headers.get("content-type", "")
                if "json" in content_type.lower():
                    try:
                        # Response is a JSON string containing base64-encoded XBRL
                        json_data = response.json()
                        if isinstance(json_data, str):
                            # Decode base64 to get actual XBRL bytes
                            import base64

                            decoded_xbrl = base64.b64decode(json_data)
                            logger.debug(
                                f"Successfully decoded base64 XBRL data: {len(decoded_xbrl)} bytes"
                            )
                            return decoded_xbrl
                        else:
                            logger.warning(
                                f"Unexpected JSON response format: {type(json_data)}"
                            )
                            return response.content
                    except Exception as e:
                        logger.warning(
                            f"Failed to decode JSON/base64 response: {e}, returning raw content"
                        )
                        return response.content
                else:
                    # Non-JSON response, return as-is
                    return response.content
            elif response.status_code == 404:
                raise NoDataError(
                    f"No data found for RSSD {rssd_id} for period {reporting_period}"
                )
            elif response.status_code == 500:
                # Server error - this endpoint may not be implemented yet
                logger.error(
                    "Server error retrieving facsimile - endpoint may not be implemented"
                )
                raise ConnectionError(
                    "RetrieveFacsimile endpoint returned server error. "
                    "This REST endpoint may not be implemented yet. "
                    "Consider using SOAP API for individual bank data retrieval."
                )
            else:
                self._handle_response(response, "RetrieveFacsimile")
                # If we get here, raise an error as we didn't get expected data
                raise ConnectionError(
                    f"Unexpected response status {response.status_code} for RetrieveFacsimile"
                )

        except Exception as e:
            logger.error(f"Failed to retrieve facsimile for RSSD {rssd_id}: {e}")
            raise

    def retrieve_panel_of_reporters(
        self, reporting_period: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve panel of reporters via REST API.

        Args:
            reporting_period: Reporting period (MM/dd/yyyy)

        Returns:
            List of institution dictionaries (normalized to SOAP format)
        """
        # REST API uses reportingPeriodEndDate as a HEADER
        # Also need dataSeries header
        params = {
            "reportingPeriodEndDate": reporting_period,
            "dataSeries": "Call",  # Default to Call series
        }

        try:
            raw_response = self._make_request("RetrievePanelOfReporters", params)

            # CRITICAL: Apply normalization to fix format differences
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrievePanelOfReporters", "REST"
            )

            # Validate response against schema
            validated = self._validate_response(
                normalized, InstitutionsResponse, "RetrievePanelOfReporters"
            )

            logger.info(
                f"Retrieved and validated {len(validated)} reporters for {reporting_period}"
            )
            return validated  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(
                f"Failed to retrieve panel of reporters for {reporting_period}: {e}"
            )
            raise

    def retrieve_filers_since_date(
        self, reporting_period: str, since_date: str
    ) -> List[str]:
        """
        Retrieve filers who submitted since date via REST API.

        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            since_date: Date since which to check submissions (MM/dd/yyyy)

        Returns:
            List of RSSD IDs as strings (normalized to SOAP format)
        """
        # REST API uses reportingPeriodEndDate and lastUpdateDateTime as HEADERS
        params = {
            "reportingPeriodEndDate": reporting_period,
            "lastUpdateDateTime": since_date,
            "dataSeries": "Call",  # Default to Call series
        }

        try:
            raw_response = self._make_request("RetrieveFilersSinceDate", params)

            # Apply normalization (REST returns integers, SOAP expects strings)
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveFilersSinceDate", "REST"
            )

            # Validate response against schema
            validated = self._validate_response(
                normalized, RSSDIDsResponse, "RetrieveFilersSinceDate"
            )

            logger.info(
                f"Retrieved and validated {len(validated)} filers since {since_date}"
            )
            return validated  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to retrieve filers since {since_date}: {e}")
            raise

    def retrieve_filers_submission_datetime(
        self, reporting_period: str, since_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve filer submission date/time info via REST API.

        Args:
            reporting_period: Reporting period (MM/dd/yyyy)
            since_date: Optional date to filter submissions since (MM/dd/yyyy)

        Returns:
            List of submission info dictionaries (normalized to SOAP format)
        """
        # REST API uses reportingPeriodEndDate and lastUpdateDateTime as HEADERS
        params = {
            "reportingPeriodEndDate": reporting_period,
            "dataSeries": "Call",  # Default to Call series
        }

        # Per PDF, lastUpdateDateTime is required for this endpoint
        if since_date:
            params["lastUpdateDateTime"] = since_date
        else:
            # Default to beginning of reporting period if not specified
            # Extract month/day/year from reporting period
            parts = reporting_period.split("/")
            if len(parts) == 3:
                # Set to first day of the quarter
                month = int(parts[0])
                year = int(parts[2])
                if month == 3:
                    params["lastUpdateDateTime"] = f"01/01/{year}"
                elif month == 6:
                    params["lastUpdateDateTime"] = f"04/01/{year}"
                elif month == 9:
                    params["lastUpdateDateTime"] = f"07/01/{year}"
                else:  # month == 12
                    params["lastUpdateDateTime"] = f"10/01/{year}"
            else:
                # Fallback to a year ago
                params["lastUpdateDateTime"] = "01/01/2023"

        try:
            raw_response = self._make_request(
                "RetrieveFilersSubmissionDateTime", params
            )

            # Apply normalization for date/time and ID format consistency
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveFilersSubmissionDateTime", "REST"
            )

            # Validate response against schema
            validated = self._validate_response(
                normalized, SubmissionsResponse, "RetrieveFilersSubmissionDateTime"
            )

            logger.info(
                f"Retrieved and validated submission info for {len(validated)} filers"
            )
            return validated  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to retrieve filer submission info: {e}")
            raise

    def retrieve_ubpr_reporting_periods(self) -> List[str]:
        """
        Retrieve available UBPR reporting periods via REST API.

        Returns:
            List of reporting period strings
        """
        # NOTE: UBPR endpoints do NOT require dataSeries header per PDF
        try:
            raw_response = self._make_request(
                "RetrieveUBPRReportingPeriods",
                params=None,  # No additional headers needed
            )

            # Apply data normalization if needed
            normalized = DataNormalizer.normalize_response(
                raw_response, "RetrieveUBPRReportingPeriods", "REST"
            )

            # Validate response against schema
            validated = self._validate_response(
                normalized, UBPRReportingPeriodsResponse, "RetrieveUBPRReportingPeriods"
            )

            logger.info(
                f"Retrieved and validated {len(validated)} UBPR reporting periods"
            )
            return validated  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to retrieve UBPR reporting periods: {e}")
            raise

    def retrieve_ubpr_xbrl_facsimile(
        self, rssd_id: Union[str, int], reporting_period: str
    ) -> bytes:
        """
        Retrieve UBPR XBRL facsimile data via REST API.

        Args:
            rssd_id: Institution RSSD ID
            reporting_period: Reporting period (MM/dd/yyyy)

        Returns:
            Raw XBRL data bytes
        """
        try:
            # UBPR endpoints do NOT require dataSeries header per PDF
            headers = self.credentials.get_auth_headers()
            headers.update(
                {
                    "reportingPeriodEndDate": reporting_period,
                    "fiIdType": "ID_RSSD",
                    "fiId": str(rssd_id),
                    # NO facsimileFormat header for UBPR (always XBRL)
                }
            )

            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()

            url = f"{self.BASE_URL}/RetrieveUBPRXBRLFacsimile"

            logger.debug(
                f"Calling RetrieveUBPRXBRLFacsimile with headers: {[k for k in headers.keys() if k != 'Authentication']}"
            )

            response = self.client.get(url, headers=headers)

            if response.status_code == 200:
                logger.info(f"Successfully retrieved UBPR facsimile for RSSD {rssd_id}")

                # Check if response is JSON (contains base64-encoded XBRL)
                content_type = response.headers.get("content-type", "")
                if "json" in content_type.lower():
                    try:
                        # Response is a JSON string containing base64-encoded XBRL
                        json_data = response.json()
                        if isinstance(json_data, str):
                            # Decode base64 to get actual XBRL bytes
                            import base64

                            decoded_xbrl = base64.b64decode(json_data)
                            logger.debug(
                                f"Successfully decoded base64 UBPR XBRL data: {len(decoded_xbrl)} bytes"
                            )
                            return decoded_xbrl
                        else:
                            logger.warning(
                                f"Unexpected JSON response format for UBPR: {type(json_data)}"
                            )
                            return response.content
                    except Exception as e:
                        logger.warning(
                            f"Failed to decode UBPR JSON/base64 response: {e}, returning raw content"
                        )
                        return response.content
                else:
                    # Non-JSON response, return as-is
                    return response.content
            elif response.status_code == 404:
                raise NoDataError(
                    f"No UBPR data found for RSSD {rssd_id} for period {reporting_period}"
                )
            else:
                self._handle_response(response, "RetrieveUBPRXBRLFacsimile")
                # If we get here, raise an error as we didn't get expected data
                raise ConnectionError(
                    f"Unexpected response status {response.status_code} for RetrieveUBPRXBRLFacsimile"
                )

        except Exception as e:
            logger.error(f"Failed to retrieve UBPR facsimile for RSSD {rssd_id}: {e}")
            raise

    @property
    def protocol_name(self) -> str:
        """Return the protocol name."""
        return "REST"

    def is_rest(self) -> bool:
        """Return True since this is a REST adapter."""
        return True


class SOAPAdapter(ProtocolAdapter):
    """
    SOAP API adapter wrapping existing functionality.

    This adapter provides a consistent interface to the existing SOAP-based
    functionality, allowing for transparent protocol selection.
    """

    def __init__(
        self,
        credentials: WebserviceCredentials,
        session: Optional["requests.Session"] = None,
    ):
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
            stacklevel=3,
        )

    def retrieve_reporting_periods(self, series: str) -> List[str]:
        """Retrieve reporting periods via SOAP (delegates to existing implementation)."""
        # Import here to avoid circular imports
        from . import methods

        # Use existing implementation
        result = methods.collect_reporting_periods(
            self.session,
            self.credentials,
            series=series,
            date_output_format="string_original",
        )
        # Ensure we return List[str] as expected by the interface
        # Since we use date_output_format="string_original", result should be List[str]
        if isinstance(result, list):
            # Runtime assertion to ensure type safety - should always be strings
            assert all(
                isinstance(x, str) for x in result
            ), f"Expected all string values, got types: {[type(x).__name__ for x in result]}"
            return result  # type: ignore[return-value]
        else:
            # Convert pandas Series to list and ensure all are strings
            result_list = result.tolist()
            assert all(
                isinstance(x, str) for x in result_list
            ), f"Expected all string values, got types: {[type(x).__name__ for x in result_list]}"
            return result_list  # type: ignore[return-value]

    def retrieve_facsimile(
        self, rssd_id: Union[str, int], reporting_period: str, series: str
    ) -> bytes:
        """Retrieve facsimile data via SOAP (delegates to existing implementation)."""
        from . import methods

        # Use existing implementation
        return methods.collect_data(  # type: ignore[no-any-return]
            self.session,
            self.credentials,
            reporting_period,
            str(rssd_id),
            series=series,
        )

    def retrieve_panel_of_reporters(
        self, reporting_period: str
    ) -> List[Dict[str, Any]]:
        """Retrieve panel of reporters via SOAP (delegates to existing implementation)."""
        from . import methods

        # Use existing implementation
        return methods.collect_filers_on_reporting_period(
            self.session, self.credentials, reporting_period
        )

    def retrieve_filers_since_date(
        self, reporting_period: str, since_date: str
    ) -> List[str]:
        """Retrieve filers since date via SOAP (delegates to existing implementation)."""
        from . import methods

        # Use existing implementation
        return methods.collect_filers_since_date(
            self.session, self.credentials, reporting_period, since_date
        )

    def retrieve_filers_submission_datetime(
        self, reporting_period: str, since_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve filer submission info via SOAP (delegates to existing implementation)."""
        from . import methods

        # Use existing implementation - note SOAP method expects since_date before reporting_period
        return methods.collect_filers_submission_date_time(
            self.session,
            self.credentials,
            since_date or reporting_period,
            reporting_period,
        )

    def retrieve_ubpr_reporting_periods(self) -> List[str]:
        """Retrieve UBPR reporting periods via SOAP (delegates to existing implementation)."""
        from . import methods

        # Use existing SOAP implementation
        return methods.collect_ubpr_reporting_periods(self.session, self.credentials)

    def retrieve_ubpr_xbrl_facsimile(
        self, rssd_id: Union[str, int], reporting_period: str
    ) -> bytes:
        """Retrieve UBPR XBRL facsimile via SOAP (delegates to existing implementation)."""
        # Use existing SOAP implementation
        # Note: SOAP methods return processed data, not raw bytes like REST
        # This cast maintains interface compatibility
        from typing import cast

        from . import methods

        result = methods.collect_ubpr_facsimile_data(
            self.session, self.credentials, str(rssd_id), reporting_period
        )
        return cast(bytes, result)

    @property
    def protocol_name(self) -> str:
        """Return the protocol name."""
        return "SOAP"

    def is_rest(self) -> bool:
        """Return False since this is a SOAP adapter."""
        return False


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
        self.call_history: list[float] = []  # Timestamps of recent calls
        self.lock = threading.Lock()

        logger.debug(
            f"Rate limiter initialized: {calls_per_hour}/hour, {calls_per_second}/sec"
        )

    def wait_if_needed(self) -> None:
        """
        Wait if needed to respect both per-second and per-hour rate limits.

        This method blocks until it's safe to make the next request.
        """
        with self.lock:
            now = time.time()

            # Clean old calls (older than 1 hour)
            hour_ago = now - 3600
            self.call_history = [
                timestamp for timestamp in self.call_history if timestamp > hour_ago
            ]

            # Check hourly limit
            if len(self.call_history) >= self.calls_per_hour:
                # Need to wait until oldest call is more than 1 hour ago
                oldest_call = self.call_history[0]
                wait_time = oldest_call + 3600 - now

                if wait_time > 0:
                    logger.warning(
                        f"Hourly rate limit reached. Waiting {wait_time:.1f} seconds"
                    )
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
                "last_call_seconds_ago": (
                    now - self.last_call if self.last_call else None
                ),
            }


def create_protocol_adapter(
    credentials: Union[WebserviceCredentials, OAuth2Credentials],
    session: Union[Optional["requests.Session"], Optional["httpx.Client"]] = None,
) -> ProtocolAdapter:
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
        # REST adapter expects httpx.Client, not requests.Session
        from typing import cast

        client_session = cast(Optional["httpx.Client"], session)
        return RESTAdapter(credentials, session=client_session)

    elif isinstance(credentials, WebserviceCredentials):
        logger.info("Creating SOAP adapter for WebserviceCredentials")
        # SOAP adapter expects requests.Session
        from typing import cast

        soap_session = cast(Optional["requests.Session"], session)
        return SOAPAdapter(credentials, session=soap_session)

    else:
        raise CredentialError(
            f"Unsupported credential type: {type(credentials)}. "
            "Use WebserviceCredentials for SOAP or OAuth2Credentials for REST."
        )
