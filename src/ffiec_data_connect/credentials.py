"""Methods to utilize for inputting credentials for the FFIEC data connection.

This module provides secure methods for inputting credentials for the FFIEC webservice data connection.

Credentials may be input via environment variables, or passing them as arguments into the class structure. Wherever possible, the credentials should not be stored in source code.

"""

import logging
import warnings
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from ffiec_data_connect.exceptions import (
    CredentialError,
    SOAPDeprecationError,
    raise_exception,
)

logger = logging.getLogger(__name__)


class CredentialType(Enum):
    """Enumerated values that represent the methods through which credentials are provided to the FFIEC webservice via the package.

    Args:
        Enum (integer): Integer that represents the credential input method
    """

    NO_CREDENTIALS = 0
    SET_FROM_INIT = 1
    SET_FROM_ENV = 2


class OAuth2Credentials:
    """
    OAuth2-based credentials for REST API access - Phase 0 Implementation.

    This credential type supports the new FFIEC REST API that uses OAuth2
    Bearer tokens for authentication instead of username/password pairs.

    Key Features:
    - OAuth2 Bearer token authentication (90-day lifecycle)
    - Token expiration tracking and validation
    - Immutable after initialization for security
    - Compatible with automatic protocol selection

    Args:
        username: FFIEC username (for UserID header)
        bearer_token: OAuth2 bearer token (90-day lifecycle)
        token_expires: Optional token expiration datetime

    Example::

        # Create OAuth2 credentials for REST API
        creds = OAuth2Credentials(
            username="your_ffiec_username",
            bearer_token="your_90_day_bearer_token",
            token_expires=datetime(2024, 3, 15)  # Optional
        )

        # Use with existing methods (automatic REST API selection)
        periods = collect_reporting_periods(session, creds)
    """

    def __init__(
        self, username: str, bearer_token: str, token_expires: Optional[datetime] = None
    ):
        """
        Initialize OAuth2 credentials for REST API access.

        Args:
            username: FFIEC username (for UserID header)
            bearer_token: OAuth2 bearer token (90-day lifecycle)
            token_expires: Token expiration datetime (optional)

        Raises:
            CredentialError: If required credentials are missing or invalid
        """
        # Validate required parameters
        if not username or not username.strip():
            raise_exception(
                CredentialError,
                "Username is required for OAuth2 credentials",
                "OAuth2 credentials require a valid FFIEC username for the UserID header. "
                "Please provide your FFIEC webservice username.",
                credential_source="oauth2_init",
            )

        if not bearer_token or not bearer_token.strip():
            raise_exception(
                CredentialError,
                "Bearer token is required for OAuth2 credentials",
                "OAuth2 credentials require a valid bearer token. "
                "Please obtain a 90-day bearer token from your FFIEC PWS account.",
                credential_source="oauth2_init",
            )

        # Warn if token appears to be hardcoded (not from env var)
        import os

        env_token = os.environ.get("FFIEC_BEARER_TOKEN", "")
        if bearer_token.strip() != env_token and env_token == "":
            import warnings

            warnings.warn(
                "Bearer token passed directly. For security, consider storing it in the "
                "FFIEC_BEARER_TOKEN environment variable:\n"
                '  export FFIEC_BEARER_TOKEN=\'eyJ...\'\n'
                "  creds = OAuth2Credentials(username=..., bearer_token=os.environ['FFIEC_BEARER_TOKEN'])",
                stacklevel=2,
            )

        # Set credentials (immutable after this point)
        self._username = username.strip()
        self._bearer_token = bearer_token.strip()

        # Auto-detect expiry from JWT payload if not explicitly provided
        if token_expires is not None:
            self._token_expires = token_expires
        else:
            self._token_expires = self._extract_jwt_expiry(self._bearer_token)  # type: ignore[assignment]

        # Set credential type for compatibility (before marking initialized)
        self.credential_source = CredentialType.SET_FROM_INIT
        self._initialized = True

        # Validate token format (test-friendly JWT validation)
        if not (
            self._bearer_token.startswith("ey")
            and self._bearer_token.endswith(".")
            and len(self._bearer_token) > 16
        ):
            raise_exception(
                CredentialError,
                "Bearer token appears invalid (wrong format)",
                "Bearer token must start with 'ey', end with '.', and be longer than 16 characters. "
                "Please verify you copied the complete JWT token from your PWS account.",
                credential_source="oauth2_init",
            )

    @property
    def username(self) -> str:
        """
        Get the FFIEC username.

        Returns:
            Username for UserID header
        """
        return self._username

    @property
    def bearer_token(self) -> str:
        """
        Get the OAuth2 bearer token.

        Returns:
            Bearer token for authentication
        """
        return self._bearer_token

    @property
    def token_expires(self) -> Optional[datetime]:
        """
        Get token expiration datetime.

        Returns:
            Token expiration datetime or None if not set
        """
        return self._token_expires

    @property
    def is_expired(self) -> bool:
        """
        Check if token is expired or expires within 24 hours.

        Returns:
            True if token is expired or expires soon, False otherwise
        """
        if not self._token_expires:
            # No expiration date set - assume valid
            return False

        # Consider expired if expires within 24 hours
        warning_time = datetime.now() + timedelta(hours=24)
        return self._token_expires <= warning_time

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for REST API requests.

        Returns:
            Dictionary containing required authentication headers
        """
        return {
            "UserID": self._username,  # Note: capital 'ID' per PDF specification
            "Authentication": f"Bearer {self._bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def test_credentials(self, session: Any = None) -> bool:
        """
        Test OAuth2 credentials against REST API (placeholder).

        Note: This will be implemented when REST adapter is available.
        For now, validates token format and expiration.

        Args:
            session: Optional requests session (for future compatibility)

        Returns:
            True if credentials appear valid, False otherwise
        """
        # Basic validation
        if not self._username or not self._bearer_token:
            return False

        # Check if token is expired
        if self.is_expired:
            logger.warning(
                "OAuth2 token is expired or expires within 24 hours."
            )
            return False

        # No live REST call is made here — we only check token shape and expiry.
        # Warn callers so they don't mistake a True return for a real credential test.
        warnings.warn(
            "test_credentials() performs only local validation (token shape + expiry); "
            "it does not make a live API call. A True return does not guarantee the "
            "FFIEC server will accept the token. Make a real request (e.g. "
            "collect_reporting_periods) to verify end-to-end.",
            UserWarning,
            stacklevel=2,
        )
        return True

    def __str__(self) -> str:
        """String representation masking sensitive data."""
        username_display = self._mask_sensitive_string(self._username)
        token_display = self._mask_sensitive_string(self._bearer_token)

        expiry_info = ""
        if self._token_expires:
            if self.is_expired:
                expiry_info = ", status='EXPIRED'"
            else:
                days_remaining = (self._token_expires - datetime.now()).days
                expiry_info = f", expires_in='{days_remaining} days'"

        return f"OAuth2Credentials(username='{username_display}', token='{token_display}'{expiry_info})"

    def __repr__(self) -> str:
        return self.__str__()

    def _mask_sensitive_string(self, value: str) -> str:
        """Mask sensitive string data, showing only first and last character."""
        if not value:
            return "***"
        if len(value) <= 2:
            return "*" * len(value)
        return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"

    @staticmethod
    def _extract_jwt_expiry(token: str) -> Optional[datetime]:
        """Extract expiration datetime from a JWT token's payload.

        FFIEC JWT tokens are unsigned (alg: "none") with a standard exp claim.
        Decoding the payload requires only base64 + json (no crypto needed).

        Returns:
            datetime if exp claim found and valid, None otherwise
        """
        import base64
        import json
        import logging

        logger = logging.getLogger(__name__)

        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            payload_b64 = parts[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes)
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Could not decode JWT payload for expiry extraction: {e}")
            return None

        exp = payload.get("exp")
        if exp is None:
            return None

        try:
            return datetime.fromtimestamp(int(exp))
        except (ValueError, OverflowError, OSError) as e:
            logger.warning(
                f"JWT 'exp' claim present but not convertible to datetime: {exp!r} ({e})"
            )
            return None

    # Prevent modification after initialization (immutable for security)
    def __setattr__(self, name: str, value: Any) -> None:
        if (
            getattr(self, "_initialized", False)
            and not name.startswith("_")
            and name != "credential_source"
        ):
            raise_exception(
                CredentialError,
                f"Cannot modify {name} after initialization",
                f"Cannot modify {name} after initialization. OAuth2Credentials are immutable for security.",
                credential_source="oauth2_modification",
            )
        super().__setattr__(name, value)


class WebserviceCredentials(object):
    """The WebserviceCredentials class. This class is used to store the credentials for the FFIEC webservice.

    Args:
        username (str, optional): FFIEC Webservice username. Optional: If not provided, the credentials will be set from the environment variable `FFIEC_USERNAME`
        password (str, optional): FFIEC Webservice password. Optional: If not provided, the credentials will be set from the environment variable `FFIEC_PASSWORD`

    Returns:
        WebserviceCredentials: An instance of the WebserviceCredentials class.

    """

    def __init__(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        raise SOAPDeprecationError(
            soap_method="WebserviceCredentials",
            rest_equivalent="OAuth2Credentials(username, bearer_token)",
            code_example=(
                "  from ffiec_data_connect import OAuth2Credentials\n"
                "\n"
                "  # Get a token at: https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx\n"
                "  creds = OAuth2Credentials(\n"
                '      username="your_ffiec_username",\n'
                '      bearer_token="eyJ...",  # 90-day JWT from FFIEC portal\n'
                "  )"
            ),
        )

    def __str__(self) -> str:  # pragma: no cover
        return "WebserviceCredentials(status='deprecated - SOAP API shut down Feb 28, 2026')"

    def __repr__(self) -> str:  # pragma: no cover
        return self.__str__()
