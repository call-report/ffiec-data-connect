"""
Unit tests for OAuth2Credentials class.

Tests OAuth2 credential handling, token validation, and expiration.

The JWT helpers in this module build real unsigned JWTs whose ``exp`` claim
encodes the desired expiration — the library reads expiry from the token
itself, so that is the only way to drive the expiration logic.
"""

import base64
import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.exceptions import CredentialError


# ---------------------------------------------------------------------------
# JWT helpers: build unsigned JWTs with a specific exp claim.
# ---------------------------------------------------------------------------


def _b64url(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def _jwt_with_exp(exp_dt: datetime) -> str:
    """Build an unsigned JWT whose payload carries ``exp = int(exp_dt.timestamp())``."""
    header = _b64url({"alg": "none", "typ": "JWT"})
    payload = _b64url({"sub": "test", "exp": int(exp_dt.timestamp())})
    return f"{header}.{payload}."


# A minimal JWT with no exp claim — useful for tests that don't care about expiry.
_JWT_NO_EXP = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."


class TestOAuth2CredentialsInitialization:
    """Test OAuth2 credential initialization scenarios."""

    def test_init_with_explicit_credentials(self):
        """Test initialization with explicit OAuth2 credentials (expiry derived from JWT)."""
        expires_at = datetime.now() + timedelta(days=90)
        token = _jwt_with_exp(expires_at)

        creds = OAuth2Credentials(username="testuser", bearer_token=token)

        assert creds.username == "testuser"
        assert creds.bearer_token == token
        # exp claim rounds to the second
        assert creds.token_expires == datetime.fromtimestamp(
            int(expires_at.timestamp())
        )
        assert not creds.is_expired

    def test_init_with_expired_token(self):
        """A JWT whose exp claim is in the past reports is_expired=True."""
        token = _jwt_with_exp(datetime.now() - timedelta(days=1))
        creds = OAuth2Credentials(username="testuser", bearer_token=token)
        assert creds.is_expired

    def test_init_with_invalid_token_format(self):
        """Test that invalid JWT format raises error."""
        with pytest.raises(ValueError) as exc_info:
            OAuth2Credentials(
                username="testuser",
                bearer_token="invalid_token",
            )

        assert (
            "JWT token" in str(exc_info.value)
            or "bearer token" in str(exc_info.value).lower()
        )

    def test_init_missing_username(self):
        """Test that missing username raises error."""
        with pytest.raises((CredentialError, ValueError, TypeError)) as exc_info:
            OAuth2Credentials(bearer_token=_JWT_NO_EXP)

        assert "username" in str(exc_info.value).lower()

    def test_init_missing_bearer_token(self):
        """Test that missing bearer token raises error."""
        with pytest.raises((CredentialError, ValueError, TypeError)) as exc_info:
            OAuth2Credentials(username="testuser")

        assert (
            "bearer" in str(exc_info.value).lower()
            or "token" in str(exc_info.value).lower()
        )

    def test_token_validation_valid_format(self):
        """Test JWT token format validation for valid tokens."""
        valid_tokens = [
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",  # Minimum valid length
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4ifQ.",
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkifQ.",
        ]

        for token in valid_tokens:
            creds = OAuth2Credentials(username="test", bearer_token=token)
            assert creds.bearer_token == token

    def test_token_validation_invalid_format(self):
        """Test JWT token format validation for invalid tokens."""
        invalid_tokens = [
            "not_a_jwt_token",
            "eY_wrong_start.",
            "eyJhbGci",  # Missing trailing dot
            "YJhbGci.",  # Wrong prefix
            "",
            ".",
        ]

        for token in invalid_tokens:
            with pytest.raises(ValueError):
                OAuth2Credentials(username="test", bearer_token=token)


class TestOAuth2CredentialsSecurity:
    """Test security aspects of OAuth2 credential handling."""

    def test_token_masking_in_str(self):
        """Test that bearer tokens are masked in string representation."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.secretpayload.",
        )

        str_repr = str(creds)

        assert "secretpayload" not in str_repr
        assert "token='e" in str_repr and "*" in str_repr

    def test_token_masking_in_repr(self):
        """Test that bearer tokens are masked in repr."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.secretpayload.",
        )

        repr_str = repr(creds)
        assert "secretpayload" not in repr_str


class TestOAuth2CredentialsExpiration:
    """Test OAuth2 credential expiration handling (driven by the JWT exp claim)."""

    def test_token_not_expired(self):
        token = _jwt_with_exp(datetime.now() + timedelta(days=30))
        creds = OAuth2Credentials(username="test", bearer_token=token)
        assert not creds.is_expired

    def test_token_expired(self):
        token = _jwt_with_exp(datetime.now() - timedelta(days=1))
        creds = OAuth2Credentials(username="test", bearer_token=token)
        assert creds.is_expired

    def test_token_expiring_soon(self):
        """Token expiring within the 24-hour warning window is reported expired."""
        token = _jwt_with_exp(datetime.now() + timedelta(hours=1))
        creds = OAuth2Credentials(username="test", bearer_token=token)
        assert creds.is_expired

    def test_token_expiration_calculation(self):
        """The exposed token_expires matches the JWT exp claim."""
        expires_at = datetime.now() + timedelta(days=90)
        token = _jwt_with_exp(expires_at)
        creds = OAuth2Credentials(username="test", bearer_token=token)

        assert creds.token_expires == datetime.fromtimestamp(
            int(expires_at.timestamp())
        )
        assert not creds.is_expired

    def test_token_expired_calculation(self):
        token = _jwt_with_exp(datetime.now() - timedelta(days=10))
        creds = OAuth2Credentials(username="test", bearer_token=token)
        assert creds.is_expired


class TestOAuth2CredentialsComparison:
    """Test OAuth2 credential comparison with WebserviceCredentials."""

    def test_oauth2_vs_webservice_detection(self):
        """Test that OAuth2 and Webservice credentials can be distinguished."""
        from ffiec_data_connect.credentials import WebserviceCredentials

        oauth_creds = OAuth2Credentials(username="test", bearer_token=_JWT_NO_EXP)

        # WebserviceCredentials now raises SOAPDeprecationError, so use a Mock
        soap_creds = Mock(spec=WebserviceCredentials)
        soap_creds.password = "password"

        assert hasattr(oauth_creds, "bearer_token")
        assert hasattr(oauth_creds, "token_expires")
        assert not hasattr(soap_creds, "bearer_token")
        assert hasattr(soap_creds, "password")


class TestTokenExpiresDeprecation:
    """The ``token_expires`` argument is deprecated and has no effect.

    The JWT's ``exp`` claim is the only authoritative source of expiration.
    """

    _JWT_EXPIRES_2026 = _jwt_with_exp(datetime(2026, 7, 20))

    def test_passing_token_expires_emits_deprecation(self):
        """Explicitly passing token_expires should emit DeprecationWarning."""
        with pytest.warns(DeprecationWarning, match="token_expires"):
            OAuth2Credentials(
                username="testuser",
                bearer_token=self._JWT_EXPIRES_2026,
                token_expires=datetime.now() + timedelta(days=90),
            )

    def test_omitting_token_expires_no_deprecation(self):
        """Omitting token_expires should NOT emit a DeprecationWarning."""
        import warnings

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            OAuth2Credentials(
                username="testuser",
                bearer_token=self._JWT_EXPIRES_2026,
            )

        deprecations = [
            w
            for w in captured
            if issubclass(w.category, DeprecationWarning)
            and "token_expires" in str(w.message)
        ]
        assert deprecations == [], (
            "Omitting token_expires should not trigger the token_expires deprecation"
        )

    def test_explicit_token_expires_is_ignored(self):
        """The deprecated arg is a no-op: the JWT exp claim always wins."""
        import warnings

        far_future = datetime(2099, 1, 1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            creds = OAuth2Credentials(
                username="testuser",
                bearer_token=self._JWT_EXPIRES_2026,
                token_expires=far_future,
            )

        # The JWT's exp (2026-07-20) wins — the explicit arg is discarded.
        assert creds.token_expires is not None
        assert creds.token_expires.year == 2026
        assert creds.token_expires != far_future

    def test_auto_extracted_expiry_when_omitted(self):
        """Omitting token_expires auto-extracts from the JWT exp claim."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self._JWT_EXPIRES_2026,
        )
        assert creds.token_expires is not None
        assert creds.token_expires.year == 2026


class TestTestCredentialsSessionDeprecation:
    """The ``session`` keyword on ``OAuth2Credentials.test_credentials()`` is a
    SOAP-era leftover. Passing it emits a DeprecationWarning but never raises.
    """

    _JWT_EXPIRES_2026 = _jwt_with_exp(datetime(2026, 7, 20))

    def test_no_session_arg_no_deprecation(self):
        """Calling test_credentials() with no args should not emit the session warning."""
        import warnings

        creds = OAuth2Credentials(
            username="testuser", bearer_token=self._JWT_EXPIRES_2026
        )

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            creds.test_credentials()

        session_warnings = [
            w
            for w in captured
            if issubclass(w.category, DeprecationWarning)
            and "session" in str(w.message).lower()
        ]
        assert session_warnings == [], (
            "Calling test_credentials() with no args should not warn about session"
        )

    def test_session_none_kwarg_warns(self):
        """Calling test_credentials(session=None) should emit DeprecationWarning."""
        creds = OAuth2Credentials(
            username="testuser", bearer_token=self._JWT_EXPIRES_2026
        )
        with pytest.warns(DeprecationWarning, match="session"):
            creds.test_credentials(session=None)

    def test_session_object_kwarg_warns_and_returns(self):
        """Passing a real session object still returns a bool and still warns."""
        creds = OAuth2Credentials(
            username="testuser", bearer_token=self._JWT_EXPIRES_2026
        )
        mock_session = Mock()
        with pytest.warns(DeprecationWarning, match="session"):
            result = creds.test_credentials(session=mock_session)
        assert isinstance(result, bool)
