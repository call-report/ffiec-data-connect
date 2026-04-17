"""
Basic unit tests for FFIEC Data Connect improvements.

Tests security, thread safety, and async functionality.
"""

import asyncio
import os
import threading
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test imports
from ffiec_data_connect import (
    AsyncCompatibleClient,
    CredentialError,
    FFIECConnection,
    ValidationError,
    WebserviceCredentials,
    __version__,
)
from ffiec_data_connect.exceptions import SOAPDeprecationError

# Helper: patch _get_connection so it returns a Mock instead of calling FFIECConnection()
_patch_get_conn = patch.object(
    AsyncCompatibleClient, "_get_connection", return_value=Mock()
)


class TestSecurity:
    """Test security improvements."""

    def test_credentials_raise_soap_deprecation(self):
        """Test that WebserviceCredentials raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("testuser123", "secretpass")

    def test_connection_raises_soap_deprecation(self):
        """Test that FFIECConnection raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            FFIECConnection()

    def test_descriptive_errors(self):
        """Test that SOAPDeprecationError provides helpful migration info."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            WebserviceCredentials()

        error = exc_info.value
        assert "WebserviceCredentials" in str(error)
        assert "OAuth2Credentials" in str(error)


class TestValidation:
    """Test input validation improvements."""

    def test_rssd_validation(self):
        """Test RSSD ID validation."""
        from ffiec_data_connect.methods import _validate_rssd_id

        # Valid IDs
        assert _validate_rssd_id("12345") == 12345
        assert _validate_rssd_id(" 67890 ") == 67890  # Strips whitespace

        # Invalid IDs
        from ffiec_data_connect.config import use_legacy_errors

        if use_legacy_errors():
            # In legacy mode, should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                _validate_rssd_id("abc123")
            assert "numeric" in str(exc_info.value)

            with pytest.raises(ValueError) as exc_info:
                _validate_rssd_id("")
            assert "empty" in str(exc_info.value)
        else:
            # In new mode, should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                _validate_rssd_id("abc123")
            assert "numeric string" in str(exc_info.value)

            with pytest.raises(ValidationError) as exc_info:
                _validate_rssd_id("")
            assert "non-empty" in str(exc_info.value)

        if use_legacy_errors():
            with pytest.raises(ValueError) as exc_info:
                _validate_rssd_id("999999999")  # Too large
            assert "out of range" in str(exc_info.value)
        else:
            with pytest.raises(ValidationError) as exc_info:
                _validate_rssd_id("999999999")  # Too large
            assert "between 1 and 99999999" in str(exc_info.value)


class TestAsyncCapabilities:
    """Test async and parallel processing capabilities."""

    @pytest.mark.asyncio
    async def test_async_client_basic(self):
        """Test basic async client functionality."""
        mock_creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(mock_creds, rate_limit=100)

        # Test that client is created
        assert client.max_concurrent == 5
        assert client.rate_limiter is not None

        # Cleanup
        client.close()

    @_patch_get_conn
    def test_parallel_processing(self, _mock_conn):
        """Test parallel data collection."""
        mock_creds = Mock(spec=WebserviceCredentials)

        with patch("ffiec_data_connect.methods.collect_data") as mock_collect:
            mock_collect.return_value = {"test": "data"}

            client = AsyncCompatibleClient(
                mock_creds, max_concurrent=2, rate_limit=None
            )

            # Collect data for multiple banks
            results = client.collect_data_parallel(
                "2020-03-31", ["12345", "67890", "11111"]
            )

            # Should have results for all banks
            assert len(results) == 3
            assert all(rssd in results for rssd in ["12345", "67890", "11111"])

        client.close()

    def test_rate_limiting(self):
        """Test that rate limiting works."""
        import time

        from ffiec_data_connect.async_compatible import RateLimiter

        limiter = RateLimiter(calls_per_second=10)

        start = time.time()
        for _ in range(3):
            limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should take at least 0.2 seconds (3 calls at 10/sec)
        assert elapsed >= 0.2

    @pytest.mark.asyncio
    @_patch_get_conn
    async def test_async_methods(self, _mock_conn):
        """Test async method execution."""
        mock_creds = Mock(spec=WebserviceCredentials)

        with patch("ffiec_data_connect.methods.collect_data") as mock_collect:
            mock_collect.return_value = {"test": "async_data"}

            async with AsyncCompatibleClient(mock_creds, rate_limit=None) as client:
                # Test async data collection
                result = await client.collect_data_async("2020-03-31", "12345")

                assert result == {"test": "async_data"}

                # Test batch async
                results = await client.collect_batch_async(
                    "2020-03-31", ["12345", "67890"]
                )

                assert len(results) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
