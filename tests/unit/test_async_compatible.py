"""
Comprehensive unit tests for async_compatible.py with async functionality focus.

Tests async/await patterns, rate limiting, parallel processing, thread safety,
and performance characteristics of the AsyncCompatibleClient.
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor
import gc

from ffiec_data_connect.async_compatible import RateLimiter, AsyncCompatibleClient
from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.ffiec_connection import FFIECConnection
from ffiec_data_connect.exceptions import RateLimitError


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(calls_per_second=5)
        
        assert limiter.calls_per_second == 5
        assert limiter.min_interval == 0.2  # 1/5
        assert limiter.last_call == 0
        assert limiter.lock is not None
    
    def test_rate_limiter_sync_blocking(self):
        """Test synchronous rate limiting with blocking."""
        limiter = RateLimiter(calls_per_second=10)  # 100ms intervals
        
        # First call should pass immediately
        start = time.time()
        limiter.wait_if_needed()
        first_duration = time.time() - start
        assert first_duration < 0.01  # Should be immediate
        
        # Second call should be delayed
        start = time.time()
        limiter.wait_if_needed()
        second_duration = time.time() - start
        assert 0.08 < second_duration < 0.12  # Should wait ~100ms
    
    @pytest.mark.asyncio
    async def test_rate_limiter_async_blocking(self):
        """Test asynchronous rate limiting with blocking."""
        limiter = RateLimiter(calls_per_second=10)  # 100ms intervals
        
        # First call should pass immediately
        start = time.time()
        await limiter.async_wait_if_needed()
        first_duration = time.time() - start
        assert first_duration < 0.01  # Should be immediate
        
        # Second call should be delayed
        start = time.time()
        await limiter.async_wait_if_needed()
        second_duration = time.time() - start
        assert 0.08 < second_duration < 0.12  # Should wait ~100ms
    
    def test_rate_limiter_thread_safety(self):
        """Test that rate limiter is thread safe."""
        limiter = RateLimiter(calls_per_second=20)
        call_times = []
        errors = []
        
        def make_calls():
            try:
                for _ in range(5):
                    start = time.time()
                    limiter.wait_if_needed()
                    call_times.append(time.time() - start)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=make_calls)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        assert len(call_times) == 15  # 3 threads * 5 calls
        
        # Most calls should be delayed (except first from each thread)
        delayed_calls = [t for t in call_times if t > 0.01]
        assert len(delayed_calls) >= 10  # Most should be rate limited


class TestAsyncCompatibleClientInitialization:
    """Test client initialization and configuration."""
    
    def test_client_initialization_defaults(self):
        """Test default initialization."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        assert client.credentials is creds
        assert client.max_concurrent == 5
        assert client.rate_limiter is not None
        assert client.rate_limiter.calls_per_second == 10
        assert client.executor is not None
        assert isinstance(client.executor, ThreadPoolExecutor)
        assert client._owned_executor is True
    
    def test_client_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        creds = Mock(spec=WebserviceCredentials)
        custom_executor = ThreadPoolExecutor(max_workers=10)
        
        client = AsyncCompatibleClient(
            creds,
            max_concurrent=3,
            rate_limit=5,
            executor=custom_executor
        )
        
        assert client.max_concurrent == 3
        assert client.rate_limiter.calls_per_second == 5
        assert client.executor is custom_executor
        assert client._owned_executor is False
    
    def test_client_initialization_no_rate_limit(self):
        """Test initialization with rate limiting disabled."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        assert client.rate_limiter is None
    
    def test_connection_caching(self):
        """Test thread-local connection caching."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        # Get connection multiple times from same thread
        conn1 = client._get_connection()
        conn2 = client._get_connection()
        
        # Should be same instance
        assert conn1 is conn2
        assert isinstance(conn1, FFIECConnection)
        
        # Should be cached
        assert threading.get_ident() in client._connection_cache


class TestSynchronousMethods:
    """Test backward-compatible synchronous methods."""
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_collect_data_sync(self, mock_collect_data):
        """Test synchronous collect_data method."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)  # Disable rate limiting for test
        
        result = client.collect_data("2023-12-31", "123456", "call")
        
        assert result == [{"test": "data"}]
        mock_collect_data.assert_called_once()
        
        # Check arguments passed to methods.collect_data
        args = mock_collect_data.call_args[0]
        assert isinstance(args[0], FFIECConnection)  # session
        assert args[1] is creds  # credentials
        assert args[2] == "2023-12-31"  # reporting_period
        assert args[3] == "123456"  # rssd_id
        assert args[4] == "call"  # series
    
    @patch('ffiec_data_connect.methods.collect_reporting_periods')
    def test_collect_reporting_periods_sync(self, mock_collect_periods):
        """Test synchronous collect_reporting_periods method."""
        mock_collect_periods.return_value = ["2023-12-31", "2023-09-30"]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        result = client.collect_reporting_periods("call", "list")
        
        assert result == ["2023-12-31", "2023-09-30"]
        mock_collect_periods.assert_called_once()
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_collect_data_with_rate_limiting(self, mock_collect_data):
        """Test that rate limiting is applied to sync methods."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=20)  # Fast rate limit for testing
        
        # Make multiple calls and time them
        start_time = time.time()
        client.collect_data("2023-12-31", "123456")
        client.collect_data("2023-12-31", "123457") 
        total_time = time.time() - start_time
        
        # Should take at least the rate limit interval
        assert total_time >= 0.04  # 1/20 = 0.05s, allow small tolerance
        assert mock_collect_data.call_count == 2


class TestParallelMethods:
    """Test parallel processing methods."""
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_collect_data_parallel(self, mock_collect_data):
        """Test parallel data collection."""
        # Mock different responses for different RSDs
        def side_effect(conn, creds, period, rssd_id, *args):
            return [{"rssd": rssd_id, "data": f"test_{rssd_id}"}]
        
        mock_collect_data.side_effect = side_effect
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, max_concurrent=3, rate_limit=None)
        
        rssd_ids = ["123456", "123457", "123458"]
        results = client.collect_data_parallel("2023-12-31", rssd_ids)
        
        # Check results
        assert len(results) == 3
        for rssd_id in rssd_ids:
            assert rssd_id in results
            assert results[rssd_id][0]["rssd"] == rssd_id
        
        # Should have been called for each RSSD
        assert mock_collect_data.call_count == 3
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_collect_data_parallel_with_errors(self, mock_collect_data):
        """Test parallel data collection with some errors."""
        def side_effect(conn, creds, period, rssd_id, *args):
            if rssd_id == "123457":
                raise Exception(f"Test error for {rssd_id}")
            return [{"rssd": rssd_id, "data": f"test_{rssd_id}"}]
        
        mock_collect_data.side_effect = side_effect
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        rssd_ids = ["123456", "123457", "123458"]
        results = client.collect_data_parallel("2023-12-31", rssd_ids)
        
        # Check results
        assert len(results) == 3
        assert "error" in results["123457"]
        assert "Test error for 123457" in results["123457"]["error"]
        
        # Successful results should be present
        assert results["123456"][0]["rssd"] == "123456"
        assert results["123458"][0]["rssd"] == "123458"
    
    def test_collect_data_parallel_progress_callback(self):
        """Test progress callback functionality."""
        with patch('ffiec_data_connect.methods.collect_data') as mock_collect:
            mock_collect.return_value = [{"test": "data"}]
            
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, rate_limit=None)
            
            progress_calls = []
            def progress_callback(rssd_id, result):
                progress_calls.append((rssd_id, result))
            
            rssd_ids = ["123456", "123457"]
            client.collect_data_parallel(
                "2023-12-31", 
                rssd_ids,
                progress_callback=progress_callback
            )
            
            # Should have progress callbacks for each RSSD
            assert len(progress_calls) == 2
            rssd_ids_from_progress = [call[0] for call in progress_calls]
            assert "123456" in rssd_ids_from_progress
            assert "123457" in rssd_ids_from_progress
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_collect_time_series(self, mock_collect_data):
        """Test time series collection for single bank."""
        def side_effect(conn, creds, period, rssd_id, *args):
            return [{"period": period, "rssd": rssd_id, "data": f"data_{period}"}]
        
        mock_collect_data.side_effect = side_effect
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        periods = ["2023-12-31", "2023-09-30", "2023-06-30"]
        results = client.collect_time_series("123456", periods)
        
        # Check results
        assert len(results) == 3
        for period in periods:
            assert period in results
            assert results[period][0]["period"] == period
            assert results[period][0]["rssd"] == "123456"
        
        assert mock_collect_data.call_count == 3


class TestAsyncMethods:
    """Test async/await methods."""
    
    @pytest.mark.asyncio
    @patch('ffiec_data_connect.methods.collect_data')
    async def test_collect_data_async(self, mock_collect_data):
        """Test async data collection."""
        mock_collect_data.return_value = [{"test": "async_data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        result = await client.collect_data_async("2023-12-31", "123456")
        
        assert result == [{"test": "async_data"}]
        mock_collect_data.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('ffiec_data_connect.methods.collect_data')
    async def test_collect_batch_async(self, mock_collect_data):
        """Test async batch collection."""
        def side_effect(conn, creds, period, rssd_id, *args):
            return [{"rssd": rssd_id, "data": f"async_test_{rssd_id}"}]
        
        mock_collect_data.side_effect = side_effect
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, max_concurrent=2, rate_limit=None)
        
        rssd_ids = ["123456", "123457", "123458"]
        results = await client.collect_batch_async("2023-12-31", rssd_ids)
        
        # Check results
        assert len(results) == 3
        for rssd_id in rssd_ids:
            assert rssd_id in results
            assert results[rssd_id][0]["rssd"] == rssd_id
    
    @pytest.mark.asyncio
    @patch('ffiec_data_connect.methods.collect_data')
    async def test_collect_batch_async_with_progress(self, mock_collect_data):
        """Test async batch with progress callback."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        progress_calls = []
        def progress_callback(rssd_id, result):
            progress_calls.append((rssd_id, result))
        
        rssd_ids = ["123456", "123457"]
        await client.collect_batch_async(
            "2023-12-31",
            rssd_ids, 
            progress_callback=progress_callback
        )
        
        # Should have progress callbacks
        assert len(progress_calls) == 2
    
    @pytest.mark.asyncio
    @patch('ffiec_data_connect.methods.collect_data')
    async def test_collect_batch_async_with_async_progress(self, mock_collect_data):
        """Test async batch with async progress callback."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        progress_calls = []
        async def async_progress_callback(rssd_id, result):
            await asyncio.sleep(0.001)  # Simulate async work
            progress_calls.append((rssd_id, result))
        
        rssd_ids = ["123456", "123457"]
        await client.collect_batch_async(
            "2023-12-31",
            rssd_ids,
            progress_callback=async_progress_callback
        )
        
        # Should have progress callbacks from async function
        assert len(progress_calls) == 2
    
    @pytest.mark.asyncio
    @patch('ffiec_data_connect.methods.collect_data')
    async def test_collect_time_series_async(self, mock_collect_data):
        """Test async time series collection."""
        def side_effect(conn, creds, period, rssd_id, *args):
            return [{"period": period, "rssd": rssd_id, "data": f"async_{period}"}]
        
        mock_collect_data.side_effect = side_effect
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        periods = ["2023-12-31", "2023-09-30"]
        results = await client.collect_time_series_async("123456", periods)
        
        # Check results
        assert len(results) == 2
        for period in periods:
            assert period in results
            assert results[period][0]["period"] == period


class TestContextManagers:
    """Test context manager support."""
    
    def test_sync_context_manager(self):
        """Test synchronous context manager."""
        creds = Mock(spec=WebserviceCredentials)
        
        with AsyncCompatibleClient(creds) as client:
            assert isinstance(client, AsyncCompatibleClient)
            # Should be able to get connections
            conn = client._get_connection()
            assert isinstance(conn, FFIECConnection)
        
        # After exit, resources should be cleaned up
        # (Specific cleanup verification would require more complex mocking)
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test asynchronous context manager."""
        creds = Mock(spec=WebserviceCredentials)
        
        async with AsyncCompatibleClient(creds) as client:
            assert isinstance(client, AsyncCompatibleClient)
            conn = client._get_connection()
            assert isinstance(conn, FFIECConnection)
        
        # After exit, resources should be cleaned up


class TestResourceManagement:
    """Test resource cleanup and management."""
    
    def test_close_method(self):
        """Test explicit resource cleanup."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        # Create some cached connections
        conn1 = client._get_connection()
        
        # Simulate another thread
        original_thread_id = threading.get_ident()
        with patch('threading.get_ident', return_value=original_thread_id + 1):
            conn2 = client._get_connection()
        
        # Should have 2 cached connections
        assert len(client._connection_cache) == 2
        
        # Close should cleanup everything
        client.close()
        
        # Cache should be empty
        assert len(client._connection_cache) == 0
    
    def test_executor_cleanup_owned(self):
        """Test executor cleanup when owned by client."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        # Should own the executor
        assert client._owned_executor is True
        
        executor = client.executor
        assert executor is not None
        
        # Mock executor shutdown to verify it's called
        with patch.object(executor, 'shutdown') as mock_shutdown:
            client.close()
            mock_shutdown.assert_called_once_with(wait=True)
    
    def test_executor_cleanup_not_owned(self):
        """Test executor cleanup when provided externally."""
        creds = Mock(spec=WebserviceCredentials)
        external_executor = ThreadPoolExecutor(max_workers=2)
        
        client = AsyncCompatibleClient(creds, executor=external_executor)
        
        # Should not own the executor
        assert client._owned_executor is False
        
        # Mock executor shutdown to verify it's NOT called
        with patch.object(external_executor, 'shutdown') as mock_shutdown:
            client.close()
            mock_shutdown.assert_not_called()
    
    def test_connection_cleanup_error_handling(self):
        """Test that connection cleanup errors are handled gracefully."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        # Get a connection and mock it to raise on close
        conn = client._get_connection()
        
        with patch.object(conn, 'close', side_effect=Exception("Close error")):
            # Should not raise exception despite connection close error
            client.close()
            
        # Cache should still be cleared
        assert len(client._connection_cache) == 0


class TestThreadSafety:
    """Test thread safety of the client."""
    
    def test_concurrent_connection_access(self):
        """Test concurrent access to connections from multiple threads."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        connections = {}
        errors = []
        
        def get_connection(thread_id):
            try:
                conn = client._get_connection()
                connections[thread_id] = conn
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=get_connection, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # Each thread should get its own connection (fewer than 10 due to thread pooling)
        assert len(connections) >= 1
        assert len(client._connection_cache) >= 1
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_concurrent_data_collection(self, mock_collect_data):
        """Test concurrent data collection."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        results = {}
        errors = []
        
        def collect_data(rssd_id):
            try:
                result = client.collect_data("2023-12-31", str(rssd_id))
                results[rssd_id] = result
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads collecting different data
        threads = []
        for i in range(5):
            t = threading.Thread(target=collect_data, args=(123456 + i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        assert len(results) == 5
        
        # Each should have gotten data
        for rssd_id in results:
            assert results[rssd_id] == [{"test": "data"}]


class TestPerformanceAndMemory:
    """Test performance characteristics and memory usage."""
    
    def test_connection_caching_efficiency(self):
        """Test that connection caching reduces object creation."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        # Get connection multiple times
        connections = []
        for _ in range(10):
            conn = client._get_connection()
            connections.append(conn)
        
        # All should be the same object (cached)
        for conn in connections:
            assert conn is connections[0]
        
        # Should only have one cached connection for this thread
        assert len(client._connection_cache) == 1
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_parallel_performance(self, mock_collect_data):
        """Test that parallel processing improves performance."""
        # Mock slow data collection
        def slow_collect_data(*args, **kwargs):
            time.sleep(0.1)  # 100ms delay
            return [{"test": "data"}]
        
        mock_collect_data.side_effect = slow_collect_data
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, max_concurrent=3, rate_limit=None)
        
        rssd_ids = ["123456", "123457", "123458"]
        
        # Time parallel execution
        start = time.time()
        results = client.collect_data_parallel("2023-12-31", rssd_ids)
        parallel_time = time.time() - start
        
        # Should complete in roughly parallel time (3 calls at ~100ms each should take ~100ms total)
        assert parallel_time < 0.2  # Should be much faster than 300ms sequential
        assert len(results) == 3
    
    def test_memory_cleanup_on_close(self):
        """Test that close() properly cleans up memory."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)
        
        # Create connections to cache
        for _ in range(5):
            client._get_connection()
        
        # Force garbage collection and check cache
        gc.collect()
        cache_size_before = len(client._connection_cache)
        assert cache_size_before >= 1
        
        # Close and verify cleanup
        client.close()
        gc.collect()
        
        assert len(client._connection_cache) == 0


class TestRateLimitingIntegration:
    """Test rate limiting integration with client methods."""
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_rate_limiting_in_parallel_collection(self, mock_collect_data):
        """Test rate limiting applied during parallel collection."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, max_concurrent=2, rate_limit=10)  # 100ms intervals
        
        rssd_ids = ["123456", "123457", "123458"]
        
        # Time the parallel collection
        start = time.time()
        results = client.collect_data_parallel("2023-12-31", rssd_ids)
        total_time = time.time() - start
        
        # Should take at least the rate limit time for 3 calls
        # With 2 concurrent workers and 100ms intervals, expect ~200ms minimum
        assert total_time >= 0.15  # Allow some tolerance
        assert len(results) == 3
    
    @pytest.mark.asyncio
    @patch('ffiec_data_connect.methods.collect_data')
    async def test_async_rate_limiting(self, mock_collect_data):
        """Test rate limiting in async methods."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=10)  # 100ms intervals
        
        # Make multiple async calls
        start = time.time()
        result1 = await client.collect_data_async("2023-12-31", "123456")
        result2 = await client.collect_data_async("2023-12-31", "123457")
        total_time = time.time() - start
        
        # Should have been rate limited
        assert total_time >= 0.08  # Allow tolerance for ~100ms delay
        assert result1 == [{"test": "data"}]
        assert result2 == [{"test": "data"}]


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_credentials_type(self):
        """Test error handling for invalid credentials."""
        # This should work at initialization but might fail at runtime
        invalid_creds = "not_credentials"
        
        # Client creation should succeed (validation happens at runtime)
        client = AsyncCompatibleClient(invalid_creds)
        assert client.credentials == "not_credentials"
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_method_call_exception_handling(self, mock_collect_data):
        """Test exception handling in method calls."""
        mock_collect_data.side_effect = Exception("Network error")
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        # Should propagate exception for single calls
        with pytest.raises(Exception) as exc_info:
            client.collect_data("2023-12-31", "123456")
        
        assert "Network error" in str(exc_info.value)
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_parallel_partial_failure_recovery(self, mock_collect_data):
        """Test recovery from partial failures in parallel processing."""
        def side_effect(*args):
            # Fail for specific RSSD
            rssd_id = args[3]  # rssd_id is 4th argument
            if rssd_id == "123457":
                raise Exception("Network timeout")
            return [{"rssd": rssd_id, "success": True}]
        
        mock_collect_data.side_effect = side_effect
        
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)
        
        rssd_ids = ["123456", "123457", "123458"]
        results = client.collect_data_parallel("2023-12-31", rssd_ids)
        
        # Should have results for all RSDs, with error for problematic one
        assert len(results) == 3
        assert "error" in results["123457"]
        assert "Network timeout" in results["123457"]["error"]
        
        # Others should succeed
        assert results["123456"][0]["success"] is True
        assert results["123458"][0]["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])