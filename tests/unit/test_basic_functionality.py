"""
Basic unit tests for FFIEC Data Connect improvements.

Tests security, thread safety, and async functionality.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import threading
import asyncio

# Test imports
from ffiec_data_connect import (
    WebserviceCredentials,
    FFIECConnection,
    AsyncCompatibleClient,
    CredentialError,
    ValidationError,
    __version__
)


class TestSecurity:
    """Test security improvements."""
    
    def test_credentials_masking(self):
        """Test that credentials are masked in string representation."""
        # Create credentials with known values
        creds = WebserviceCredentials("testuser123", "secretpass")
        
        # String representation should mask sensitive data
        str_repr = str(creds)
        assert "testuser123" not in str_repr
        assert "secretpass" not in str_repr
        assert "t*********3" in str_repr or "***" in str_repr
        
    def test_proxy_masking(self):
        """Test that proxy credentials are masked."""
        conn = FFIECConnection()
        conn.proxy_host = "proxy.example.com"
        conn.proxy_user_name = "proxyuser"
        conn.proxy_password = "proxypass"
        
        str_repr = str(conn)
        assert "proxy.example.com" not in str_repr
        assert "proxyuser" not in str_repr
        assert "proxypass" not in str_repr
        assert "example.com" in str_repr  # Should show domain only
    
    def test_descriptive_errors(self):
        """Test that errors provide helpful context."""
        with pytest.raises(CredentialError) as exc_info:
            WebserviceCredentials()  # No credentials provided
        
        error = exc_info.value
        assert "FFIEC_USERNAME" in str(error)
        assert "environment variable" in str(error)


class TestThreadSafety:
    """Test thread safety improvements."""
    
    def test_connection_thread_safe(self):
        """Test that FFIECConnection is thread-safe."""
        conn = FFIECConnection()
        results = []
        errors = []
        
        def modify_proxy(port):
            try:
                conn.proxy_port = port
                conn.proxy_host = f"proxy{port}.com"
                # Verify settings
                assert conn.proxy_port == port
                results.append(port)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads modifying connection
        threads = []
        for i in range(10):
            t = threading.Thread(target=modify_proxy, args=(8080 + i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        assert len(results) == 10
    
    def test_session_cleanup(self):
        """Test that sessions are properly cleaned up."""
        conn = FFIECConnection()
        
        # Access session to create it
        _ = conn.session
        assert conn._session is not None
        
        # Close should cleanup
        conn.close()
        assert conn._session is None
        
    def test_context_manager(self):
        """Test context manager for automatic cleanup."""
        with FFIECConnection() as conn:
            # Session should be available
            session = conn.session
            assert session is not None
        
        # After context, should be cleaned up
        assert conn._session is None


class TestValidation:
    """Test input validation improvements."""
    
    def test_rssd_validation(self):
        """Test RSSD ID validation."""
        from ffiec_data_connect.methods import _validate_rssd_id
        
        # Valid IDs
        assert _validate_rssd_id("12345") == 12345
        assert _validate_rssd_id(" 67890 ") == 67890  # Strips whitespace
        
        # Invalid IDs
        with pytest.raises(ValidationError) as exc_info:
            _validate_rssd_id("abc123")
        assert "numeric string" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            _validate_rssd_id("")
        assert "non-empty" in str(exc_info.value)
        
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
    
    def test_parallel_processing(self):
        """Test parallel data collection."""
        mock_creds = Mock(spec=WebserviceCredentials)
        
        with patch('ffiec_data_connect.methods.collect_data') as mock_collect:
            mock_collect.return_value = {'test': 'data'}
            
            client = AsyncCompatibleClient(mock_creds, max_concurrent=2, rate_limit=None)
            
            # Collect data for multiple banks
            results = client.collect_data_parallel(
                "2020-03-31",
                ["12345", "67890", "11111"]
            )
            
            # Should have results for all banks
            assert len(results) == 3
            assert all(rssd in results for rssd in ["12345", "67890", "11111"])
        
        client.close()
    
    def test_rate_limiting(self):
        """Test that rate limiting works."""
        from ffiec_data_connect.async_compatible import RateLimiter
        import time
        
        limiter = RateLimiter(calls_per_second=10)
        
        start = time.time()
        for _ in range(3):
            limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Should take at least 0.2 seconds (3 calls at 10/sec)
        assert elapsed >= 0.2
    
    @pytest.mark.asyncio
    async def test_async_methods(self):
        """Test async method execution."""
        mock_creds = Mock(spec=WebserviceCredentials)
        
        with patch('ffiec_data_connect.methods.collect_data') as mock_collect:
            mock_collect.return_value = {'test': 'async_data'}
            
            async with AsyncCompatibleClient(mock_creds, rate_limit=None) as client:
                # Test async data collection
                result = await client.collect_data_async(
                    "2020-03-31",
                    "12345"
                )
                
                assert result == {'test': 'async_data'}
                
                # Test batch async
                results = await client.collect_batch_async(
                    "2020-03-31",
                    ["12345", "67890"]
                )
                
                assert len(results) == 2


class TestMemoryManagement:
    """Test memory leak fixes."""
    
    def test_no_session_leak_on_property_change(self):
        """Test that changing properties doesn't leak sessions."""
        conn = FFIECConnection()
        
        # Track sessions
        sessions = []
        
        # Change properties multiple times
        for i in range(5):
            conn.proxy_port = 8080 + i
            if conn._session:
                sessions.append(conn._session)
        
        # Only the last session should be active
        # Previous ones should have been closed
        conn.close()
    
    def test_cleanup_all_instances(self):
        """Test class-level cleanup method."""
        # Create multiple connections
        conns = [FFIECConnection() for _ in range(3)]
        
        # Access sessions to create them
        for conn in conns:
            _ = conn.session
        
        # Cleanup all
        FFIECConnection.cleanup_all()
        
        # All should be cleaned
        for conn in conns:
            assert conn._session is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])