"""
Unit tests for OAuth2Credentials class.

Tests OAuth2 credential handling, token validation, and expiration.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.exceptions import CredentialError


class TestOAuth2CredentialsInitialization:
    """Test OAuth2 credential initialization scenarios."""

    def test_init_with_explicit_credentials(self):
        """Test initialization with explicit OAuth2 credentials."""
        token_expires = datetime.now() + timedelta(days=90)
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.test.",
            token_expires=token_expires
        )

        assert creds.username == "testuser"
        assert creds.bearer_token == "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.test."
        assert creds.token_expires == token_expires
        assert not creds.is_expired

    def test_init_with_expired_token(self):
        """Test initialization with expired token shows warning."""
        token_expires = datetime.now() - timedelta(days=1)
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.test.",
            token_expires=token_expires
        )

        assert creds.is_expired

    def test_init_with_invalid_token_format(self):
        """Test that invalid JWT format raises error."""
        with pytest.raises(ValueError) as exc_info:
            OAuth2Credentials(
                username="testuser",
                bearer_token="invalid_token",  # Should start with 'ey' and end with '.'
                token_expires=datetime.now() + timedelta(days=90)
            )
        
        assert "JWT token" in str(exc_info.value) or "bearer token" in str(exc_info.value).lower()

    def test_init_missing_username(self):
        """Test that missing username raises error."""
        with pytest.raises((CredentialError, ValueError, TypeError)) as exc_info:
            OAuth2Credentials(
                bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.test.",
                token_expires=datetime.now() + timedelta(days=90)
            )
        
        assert "username" in str(exc_info.value).lower()

    def test_init_missing_bearer_token(self):
        """Test that missing bearer token raises error."""
        with pytest.raises((CredentialError, ValueError, TypeError)) as exc_info:
            OAuth2Credentials(
                username="testuser",
                token_expires=datetime.now() + timedelta(days=90)
            )
        
        assert "bearer" in str(exc_info.value).lower() or "token" in str(exc_info.value).lower()

    def test_token_validation_valid_format(self):
        """Test JWT token format validation for valid tokens."""
        valid_tokens = [
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",  # Minimum valid length
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4ifQ.",
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkifQ.",
        ]
        
        for token in valid_tokens:
            creds = OAuth2Credentials(
                username="test",
                bearer_token=token,
                token_expires=datetime.now() + timedelta(days=90)
            )
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
                OAuth2Credentials(
                    username="test",
                    bearer_token=token,
                    token_expires=datetime.now() + timedelta(days=90)
                )


class TestOAuth2CredentialsSecurity:
    """Test security aspects of OAuth2 credential handling."""

    def test_token_masking_in_str(self):
        """Test that bearer tokens are masked in string representation."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.secretpayload.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        
        str_repr = str(creds)
        
        # Should not contain actual token payload
        assert "secretpayload" not in str_repr
        
        # Should contain masked version (starts with 'e' and has asterisks)
        assert "token='e" in str_repr and "*" in str_repr

    def test_token_masking_in_repr(self):
        """Test that bearer tokens are masked in repr."""
        creds = OAuth2Credentials(
            username="testuser",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.secretpayload.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        
        repr_str = repr(creds)
        
        # Should not contain full token
        assert "secretpayload" not in repr_str


class TestOAuth2CredentialsExpiration:
    """Test OAuth2 credential expiration handling."""

    def test_token_not_expired(self):
        """Test token that is not expired."""
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",
            token_expires=datetime.now() + timedelta(days=30)
        )
        
        assert not creds.is_expired

    def test_token_expired(self):
        """Test token that is expired."""
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",
            token_expires=datetime.now() - timedelta(days=1)
        )
        
        assert creds.is_expired

    def test_token_expiring_soon(self):
        """Test token expiring within warning threshold."""
        # Token expiring in 1 hour (within 24-hour warning threshold)
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",
            token_expires=datetime.now() + timedelta(hours=1)
        )
        
        # Should be marked as expired since it expires within 24 hours
        assert creds.is_expired  # is_expired returns True for tokens expiring within 24 hours

    def test_token_expiration_calculation(self):
        """Test token expiration time calculation."""
        days_ahead = 90  # Tokens expire within 90 days for the service
        expires_at = datetime.now() + timedelta(days=days_ahead)
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",
            token_expires=expires_at
        )
        
        # Check that expiration is set correctly
        assert creds.token_expires == expires_at
        assert not creds.is_expired  # Should not be expired (90 days > 24 hour threshold)

    def test_token_expired_calculation(self):
        """Test expired token detection."""
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",
            token_expires=datetime.now() - timedelta(days=10)
        )
        
        # Should be marked as expired
        assert creds.is_expired


class TestOAuth2CredentialsComparison:
    """Test OAuth2 credential comparison with WebserviceCredentials."""

    def test_oauth2_vs_webservice_detection(self):
        """Test that OAuth2 and Webservice credentials can be distinguished."""
        from ffiec_data_connect.credentials import WebserviceCredentials
        
        oauth_creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        
        soap_creds = WebserviceCredentials(
            username="test",
            password="password"
        )
        
        # Check that they have different attributes
        assert hasattr(oauth_creds, 'bearer_token')
        assert hasattr(oauth_creds, 'token_expires')
        assert not hasattr(soap_creds, 'bearer_token')
        assert hasattr(soap_creds, 'password')