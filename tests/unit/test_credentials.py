"""
Comprehensive unit tests for credentials.py with security focus.

Tests credential handling, security features, and thread safety.
"""

import os
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from requests import Session

from ffiec_data_connect.credentials import CredentialType, OAuth2Credentials, WebserviceCredentials
from ffiec_data_connect.exceptions import ConnectionError, CredentialError, SOAPDeprecationError
from ffiec_data_connect.ffiec_connection import FFIECConnection


class TestWebserviceCredentialsInitialization:
    """Test that WebserviceCredentials raises SOAPDeprecationError on any instantiation."""

    def test_init_with_explicit_credentials_raises_soap_deprecation(self):
        """Test that initialization with explicit username and password raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("testuser", "testpass")

    @patch.dict(os.environ, {"FFIEC_USERNAME": "envuser", "FFIEC_PASSWORD": "envpass"})
    def test_init_from_environment_raises_soap_deprecation(self):
        """Test that initialization from environment variables raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials()

    @patch.dict(os.environ, {"FFIEC_USERNAME": "envuser", "FFIEC_PASSWORD": "envpass"})
    def test_explicit_overrides_environment_raises_soap_deprecation(self):
        """Test that explicit credentials also raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("explicituser", "explicitpass")

    def test_missing_credentials_raises_soap_deprecation(self):
        """Test that missing credentials still raise SOAPDeprecationError (before any validation)."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SOAPDeprecationError):
                WebserviceCredentials()

    @patch.dict(os.environ, {"FFIEC_USERNAME": "onlyuser"})
    def test_missing_password_only_raises_soap_deprecation(self):
        """Test that missing password still raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials()

    @patch.dict(os.environ, {"FFIEC_PASSWORD": "onlypass"})
    def test_missing_username_only_raises_soap_deprecation(self):
        """Test that missing username still raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials()


class TestWebserviceCredentialsSOAPDeprecationMessage:
    """Test that the SOAPDeprecationError contains useful migration guidance."""

    def test_deprecation_error_mentions_oauth2(self):
        """Test that the deprecation error mentions OAuth2Credentials as the replacement."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            WebserviceCredentials("user", "pass")

        assert exc_info.value.rest_equivalent == "OAuth2Credentials(username, bearer_token)"

    def test_deprecation_error_soap_method_name(self):
        """Test that the deprecation error identifies the deprecated method."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            WebserviceCredentials()

        assert exc_info.value.soap_method == "WebserviceCredentials"

    def test_deprecation_error_has_code_example(self):
        """Test that the deprecation error includes a migration code example."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            WebserviceCredentials("user", "pass")

        assert "OAuth2Credentials" in exc_info.value.code_example
        assert "bearer_token" in exc_info.value.code_example


class TestWebserviceCredentialsClassStillExists:
    """Test that WebserviceCredentials class shell remains for isinstance checks."""

    def test_class_is_importable(self):
        """Test that WebserviceCredentials can still be imported."""
        assert WebserviceCredentials is not None

    def test_class_is_a_type(self):
        """Test that WebserviceCredentials is still a class."""
        assert isinstance(WebserviceCredentials, type)


class TestCredentialSecurity:
    """Test security aspects of credential handling (using SOAPDeprecationError)."""

    def test_webservice_credentials_cannot_be_instantiated(self):
        """Confirm that all instantiation paths raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("testuser123", "secretpassword")

    def test_webservice_credentials_no_args_cannot_be_instantiated(self):
        """Confirm no-arg instantiation raises SOAPDeprecationError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SOAPDeprecationError):
                WebserviceCredentials()


class TestCredentialImmutability:
    """Test credential immutability for security (SOAPDeprecationError blocks init)."""

    def test_cannot_instantiate_to_modify(self):
        """Test that WebserviceCredentials cannot even be instantiated."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("originaluser", "originalpass")

    def test_immutability_thread_safety(self):
        """Test that instantiation raises SOAPDeprecationError from multiple threads."""
        errors = []

        def try_create_credentials():
            try:
                WebserviceCredentials("user", "pass")
                errors.append("Instantiation succeeded - should have raised SOAPDeprecationError")
            except SOAPDeprecationError:
                pass  # Expected
            except Exception as e:
                errors.append(f"Wrong exception type: {type(e).__name__}")

        threads = []
        for i in range(10):
            t = threading.Thread(target=try_create_credentials)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCredentialValidation:
    """Test that WebserviceCredentials raises SOAPDeprecationError before any validation."""

    def test_validation_blocked_by_deprecation(self):
        """Test that credential validation is blocked because init raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            creds = WebserviceCredentials("validuser", "validpass")

    def test_validation_blocked_for_bad_credentials(self):
        """Test that even bad credentials raise SOAPDeprecationError before validation."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("baduser", "badpass")


class TestCredentialTypes:
    """Test credential type enumeration and detection."""

    def test_credential_type_enum_values(self):
        """Test CredentialType enum values."""
        assert CredentialType.NO_CREDENTIALS.value == 0
        assert CredentialType.SET_FROM_INIT.value == 1
        assert CredentialType.SET_FROM_ENV.value == 2

    def test_credential_source_detection_init_raises_deprecation(self):
        """Test that credential source detection for init raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("user", "pass")

    @patch.dict(os.environ, {"FFIEC_USERNAME": "envuser", "FFIEC_PASSWORD": "envpass"})
    def test_credential_source_detection_env_raises_deprecation(self):
        """Test that credential source detection for environment raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials()


class TestThreadSafety:
    """Test thread safety of credential operations."""

    def test_concurrent_credential_creation_raises_deprecation(self):
        """Test concurrent credential creation all raise SOAPDeprecationError."""
        results = []
        errors = []

        def create_credentials(index):
            try:
                WebserviceCredentials(f"user{index}", f"pass{index}")
                errors.append(f"Thread {index}: instantiation succeeded unexpectedly")
            except SOAPDeprecationError:
                results.append(index)
            except Exception as e:
                errors.append(f"Thread {index}: wrong exception {type(e).__name__}")

        threads = []
        for i in range(20):
            t = threading.Thread(target=create_credentials, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_credentials_raises_deprecation(self):
        """Test that empty string credentials raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("", "password")

        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("username", "")

    def test_none_credentials_raises_deprecation(self):
        """Test that None credentials raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials(None, "password")

        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("username", None)

    def test_whitespace_credentials_raises_deprecation(self):
        """Test that whitespace-only credentials raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("   ", "password")

        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("username", "   ")

    def test_very_long_credentials_raises_deprecation(self):
        """Test that very long credentials raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("a" * 1000, "b" * 1000)

    def test_unicode_credentials_raises_deprecation(self):
        """Test that Unicode credentials raise SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("\u7528\u6237\u540d", "\u5bc6\u7801")


class TestOAuth2CredentialsJWTExpiryAutoDetection:
    """Test the JWT expiry auto-detection feature of OAuth2Credentials."""

    def test_jwt_expiry_extracted_when_no_token_expires_provided(self):
        """OAuth2Credentials with no token_expires but a valid JWT extracts exp from payload."""
        # Token payload: {"sub": "test", "exp": 1783442253}
        test_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."

        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=test_token,
        )

        assert creds.token_expires is not None
        assert creds.token_expires == datetime.fromtimestamp(1783442253)

    def test_explicit_token_expires_takes_precedence(self):
        """When token_expires is explicitly provided, it takes precedence over JWT exp."""
        test_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
        explicit_expires = datetime(2030, 1, 1)

        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=test_token,
            token_expires=explicit_expires,
        )

        assert creds.token_expires == explicit_expires

    def test_jwt_without_exp_claim_returns_none(self):
        """A JWT without an exp claim results in token_expires being None."""
        # Token payload: {"sub": "test"} (no exp claim)
        # Header: {"alg":"none","typ":"JWT"} -> eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0
        # Payload: {"sub":"test"} -> eyJzdWIiOiJ0ZXN0In0
        import base64
        import json

        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "test"}).encode()).decode().rstrip("=")
        test_token = f"{header}.{payload}."

        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=test_token,
        )

        assert creds.token_expires is None


class TestOAuth2CredentialsCoverage:
    """Additional tests for full coverage of OAuth2Credentials."""

    # Valid (non-expired) JWT: exp=1783442253 (~2026-07-06)
    VALID_TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
    # Expired JWT: exp=1000000000 (~2001-09-09)
    EXPIRED_TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ."

    @pytest.fixture(autouse=True)
    def _disable_legacy_errors(self):
        """Disable legacy errors so specific exception types are raised."""
        from ffiec_data_connect.config import Config
        Config.set_legacy_errors(False)
        yield

    def test_empty_username_raises_credential_error(self):
        """OAuth2Credentials with empty string username raises CredentialError (line 82)."""
        with pytest.raises(CredentialError):
            OAuth2Credentials(
                username="",
                bearer_token=self.VALID_TOKEN,
            )

    def test_whitespace_only_username_raises_credential_error(self):
        """OAuth2Credentials with whitespace-only username raises CredentialError."""
        with pytest.raises(CredentialError):
            OAuth2Credentials(
                username="   ",
                bearer_token=self.VALID_TOKEN,
            )

    def test_is_expired_when_token_expires_is_none(self):
        """is_expired returns False when token_expires is None (line 167)."""
        import base64
        import json

        # JWT without exp claim -> token_expires will be None
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "test"}).encode()).decode().rstrip("=")
        no_exp_token = f"{header}.{payload}."

        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=no_exp_token,
        )

        assert creds.token_expires is None
        assert creds.is_expired is False

    def test_test_credentials_expired_token_returns_false(self):
        """test_credentials() returns False for expired token (lines 201-211)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.EXPIRED_TOKEN,
        )

        assert creds.is_expired is True
        assert creds.test_credentials() is False

    def test_test_credentials_valid_token_returns_true(self):
        """test_credentials() returns True for valid token (lines 201-211)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        assert creds.is_expired is False
        assert creds.test_credentials() is True

    def test_str_expired_token_shows_expired(self):
        """__str__ with expired token shows 'EXPIRED' (line 221)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.EXPIRED_TOKEN,
        )

        result = str(creds)
        assert "EXPIRED" in result

    def test_str_valid_token_shows_days(self):
        """__str__ with valid token shows days remaining (line 226)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        result = str(creds)
        assert "days" in result

    def test_mask_sensitive_string_short(self):
        """_mask_sensitive_string with len<=2 returns all asterisks (line 234, 236)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        # len <= 2
        assert creds._mask_sensitive_string("ab") == "**"
        assert creds._mask_sensitive_string("a") == "*"

    def test_mask_sensitive_string_normal(self):
        """_mask_sensitive_string with normal len shows first and last char (line 236)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        result = creds._mask_sensitive_string("hello")
        assert result == "h***o"

    def test_mask_sensitive_string_empty(self):
        """_mask_sensitive_string with empty string returns '***' (line 234)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        assert creds._mask_sensitive_string("") == "***"

    def test_extract_jwt_expiry_invalid_base64(self):
        """_extract_jwt_expiry with invalid base64 payload returns None (lines 263-265)."""
        # A token where the payload section is not valid base64
        result = OAuth2Credentials._extract_jwt_expiry("eyJhbGciOiJub25lIn0.!!!invalid-base64!!!.")
        assert result is None

    def test_extract_jwt_expiry_overflow_exp(self):
        """_extract_jwt_expiry with overflow exp value returns None (lines 273-277)."""
        import base64
        import json

        header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
        # Use an absurdly large exp that causes OverflowError in datetime.fromtimestamp
        payload = base64.urlsafe_b64encode(json.dumps({"exp": 999999999999999999}).encode()).decode().rstrip("=")
        overflow_token = f"{header}.{payload}."

        result = OAuth2Credentials._extract_jwt_expiry(overflow_token)
        assert result is None

    def test_setattr_immutability_after_init(self):
        """Setting a public attribute after init raises CredentialError (line 286)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        with pytest.raises(CredentialError):
            creds.some_new_attribute = "value"

    def test_repr_delegates_to_str(self):
        """__repr__ returns same result as __str__."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )

        assert repr(creds) == str(creds)


class TestOAuth2CredentialsMissingCoverage:
    """Additional tests to cover remaining uncovered lines in credentials.py."""

    VALID_TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
    EXPIRED_TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ."

    @pytest.fixture(autouse=True)
    def _disable_legacy_errors(self):
        from ffiec_data_connect.config import Config
        Config.set_legacy_errors(False)
        yield

    def test_test_credentials_empty_username_returns_false(self):
        """test_credentials() returns False when username is empty (line 202).

        We bypass __init__ validation by patching the username after creation.
        """
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )
        # Force empty username to trigger line 201-202
        object.__setattr__(creds, "_username", "")
        assert creds.test_credentials() is False

    def test_test_credentials_empty_token_returns_false(self):
        """test_credentials() returns False when bearer_token is empty (line 202)."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
        )
        # Force empty token to trigger line 201-202
        object.__setattr__(creds, "_bearer_token", "")
        assert creds.test_credentials() is False

    def test_str_token_expires_within_24h_shows_expired(self):
        """__str__ shows 'EXPIRED' when token_expires is set but within 24 hours (line 219->226).

        token_expires is set (truthy) and is_expired is True because it falls
        within the 24-hour warning window.
        """
        from datetime import timedelta

        # Token that expires in 12 hours -> is_expired returns True (within 24h)
        expires_soon = datetime.now() + timedelta(hours=12)
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token=self.VALID_TOKEN,
            token_expires=expires_soon,
        )

        assert creds.is_expired is True
        result = str(creds)
        assert "EXPIRED" in result

    def test_jwt_payload_needing_base64_padding(self):
        """JWT payload segment that needs padding (line 260: payload_b64 += '=' * ...).

        The payload 'eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwfQ' is 41 chars
        which needs 3 '=' padding to reach a multiple of 4.
        """
        import base64
        import json

        # Create a payload whose base64 encoding is NOT a multiple of 4
        payload = {"sub": "a", "exp": 1783442253}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        # Verify it actually needs padding
        assert len(payload_b64) % 4 != 0

        header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        token = f"{header_b64}.{payload_b64}."

        result = OAuth2Credentials._extract_jwt_expiry(token)
        assert result == datetime.fromtimestamp(1783442253)


class TestWebserviceCredentialsReprCoverage:
    """Test WebserviceCredentials.__repr__ (line 325/328).

    Since __init__ raises SOAPDeprecationError, __repr__ is unreachable
    through normal construction. We mark it with pragma: no cover in source.
    """

    def test_webservice_credentials_str_and_repr_unreachable(self):
        """Confirm that WebserviceCredentials cannot be instantiated to reach __str__/__repr__."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("user", "pass")


class TestExtractJwtExpiryEdgeCases:
    """Cover line 258: token with < 2 parts."""

    def test_token_no_dots_returns_none(self):
        result = OAuth2Credentials._extract_jwt_expiry("nodots")
        assert result is None

    def test_token_single_dot_returns_none(self):
        result = OAuth2Credentials._extract_jwt_expiry("one.")
        assert result is None


class TestOAuth2StrNoTokenExpires:
    """Cover branch 219->226: __str__ when token_expires is None."""

    def test_str_no_token_expires(self):
        """JWT without exp claim → token_expires=None → no expiry info in str."""
        # JWT with no exp claim
        import base64
        import json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "test"}).encode()).rstrip(b"=").decode()
        token = f"{header}.{payload}."

        creds = OAuth2Credentials(username="user", bearer_token=token)
        assert creds.token_expires is None
        s = str(creds)
        assert "expires_in" not in s
        assert "EXPIRED" not in s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
