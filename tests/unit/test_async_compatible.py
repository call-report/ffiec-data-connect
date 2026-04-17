"""
Comprehensive unit tests for async_compatible.py with async functionality focus.

Tests async/await patterns, rate limiting, parallel processing, thread safety,
and performance characteristics of the AsyncCompatibleClient.
"""

import asyncio
import gc
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ffiec_data_connect.async_compatible import AsyncCompatibleClient, RateLimiter
from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.exceptions import RateLimitError, SOAPDeprecationError
from ffiec_data_connect.ffiec_connection import FFIECConnection

# Helper: patch _get_connection so it returns a Mock instead of calling FFIECConnection()
_patch_get_conn = patch.object(
    AsyncCompatibleClient, "_get_connection", return_value=Mock()
)


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
            creds, max_concurrent=3, rate_limit=5, executor=custom_executor
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

    def test_connection_caching_raises_for_soap(self):
        """Test that _get_connection raises SOAPDeprecationError since FFIECConnection is deprecated."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)

        # _get_connection calls FFIECConnection() which now raises SOAPDeprecationError
        with pytest.raises(SOAPDeprecationError):
            client._get_connection()


class TestSynchronousMethods:
    """Test backward-compatible synchronous methods."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_collect_data_sync(self, mock_collect_data, _mock_conn):
        """Test synchronous collect_data method."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(
            creds, rate_limit=None
        )  # Disable rate limiting for test

        result = client.collect_data("2023-12-31", "123456", "call")

        assert result == [{"test": "data"}]
        mock_collect_data.assert_called_once()

        # Check arguments passed to methods.collect_data
        args = mock_collect_data.call_args[0]
        assert args[1] is creds  # credentials
        assert args[2] == "2023-12-31"  # reporting_period
        assert args[3] == "123456"  # rssd_id
        assert args[4] == "call"  # series

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_reporting_periods")
    def test_collect_reporting_periods_sync(self, mock_collect_periods, _mock_conn):
        """Test synchronous collect_reporting_periods method."""
        mock_collect_periods.return_value = ["2023-12-31", "2023-09-30"]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        result = client.collect_reporting_periods("call", "list")

        assert result == ["2023-12-31", "2023-09-30"]
        mock_collect_periods.assert_called_once()

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_collect_data_with_rate_limiting(self, mock_collect_data, _mock_conn):
        """Test that rate limiting is applied to sync methods."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(
            creds, rate_limit=20
        )  # Fast rate limit for testing

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

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_collect_data_parallel(self, mock_collect_data, _mock_conn):
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

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_collect_data_parallel_with_errors(self, mock_collect_data, _mock_conn):
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

    @_patch_get_conn
    def test_collect_data_parallel_progress_callback(self, _mock_conn):
        """Test progress callback functionality."""
        with patch("ffiec_data_connect.methods.collect_data") as mock_collect:
            mock_collect.return_value = [{"test": "data"}]

            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, rate_limit=None)

            progress_calls = []

            def progress_callback(rssd_id, result):
                progress_calls.append((rssd_id, result))

            rssd_ids = ["123456", "123457"]
            client.collect_data_parallel(
                "2023-12-31", rssd_ids, progress_callback=progress_callback
            )

            # Should have progress callbacks for each RSSD
            assert len(progress_calls) == 2
            rssd_ids_from_progress = [call[0] for call in progress_calls]
            assert "123456" in rssd_ids_from_progress
            assert "123457" in rssd_ids_from_progress

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_collect_time_series(self, mock_collect_data, _mock_conn):
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
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_collect_data_async(self, mock_collect_data, _mock_conn):
        """Test async data collection."""
        mock_collect_data.return_value = [{"test": "async_data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        result = await client.collect_data_async("2023-12-31", "123456")

        assert result == [{"test": "async_data"}]
        mock_collect_data.assert_called_once()

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_collect_batch_async(self, mock_collect_data, _mock_conn):
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
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_collect_batch_async_with_progress(
        self, mock_collect_data, _mock_conn
    ):
        """Test async batch with progress callback."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        progress_calls = []

        def progress_callback(rssd_id, result):
            progress_calls.append((rssd_id, result))

        rssd_ids = ["123456", "123457"]
        await client.collect_batch_async(
            "2023-12-31", rssd_ids, progress_callback=progress_callback
        )

        # Should have progress callbacks
        assert len(progress_calls) == 2

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_collect_batch_async_with_async_progress(
        self, mock_collect_data, _mock_conn
    ):
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
            "2023-12-31", rssd_ids, progress_callback=async_progress_callback
        )

        # Should have progress callbacks from async function
        assert len(progress_calls) == 2

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_collect_time_series_async(self, mock_collect_data, _mock_conn):
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

        # After exit, resources should be cleaned up

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test asynchronous context manager."""
        creds = Mock(spec=WebserviceCredentials)

        async with AsyncCompatibleClient(creds) as client:
            assert isinstance(client, AsyncCompatibleClient)

        # After exit, resources should be cleaned up


class TestResourceManagement:
    """Test resource cleanup and management."""

    def test_close_method(self):
        """Test explicit resource cleanup."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)

        # Manually inject mock connections into the cache to test cleanup
        mock_conn1 = Mock()
        mock_conn2 = Mock()
        thread_id = threading.get_ident()
        client._connection_cache[thread_id] = mock_conn1
        client._connection_cache[thread_id + 1] = mock_conn2

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
        with patch.object(executor, "shutdown") as mock_shutdown:
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
        with patch.object(external_executor, "shutdown") as mock_shutdown:
            client.close()
            mock_shutdown.assert_not_called()

    def test_connection_cleanup_error_handling(self):
        """Test that connection cleanup errors are handled gracefully."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)

        # Manually inject a mock connection that raises on close
        mock_conn = Mock()
        mock_conn.close.side_effect = Exception("Close error")
        thread_id = threading.get_ident()
        client._connection_cache[thread_id] = mock_conn

        # Should not raise exception despite connection close error
        client.close()

        # Cache should still be cleared
        assert len(client._connection_cache) == 0


class TestThreadSafety:
    """Test thread safety of the client."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_concurrent_data_collection(self, mock_collect_data, _mock_conn):
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

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_parallel_performance(self, mock_collect_data, _mock_conn):
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

        # Inject mock connections into cache
        for i in range(5):
            client._connection_cache[i] = Mock()

        # Force garbage collection and check cache
        gc.collect()
        cache_size_before = len(client._connection_cache)
        assert cache_size_before == 5

        # Close and verify cleanup
        client.close()
        gc.collect()

        assert len(client._connection_cache) == 0


class TestRateLimitingIntegration:
    """Test rate limiting integration with client methods."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_rate_limiting_in_parallel_collection(self, mock_collect_data, _mock_conn):
        """Test rate limiting applied during parallel collection."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(
            creds, max_concurrent=2, rate_limit=10
        )  # 100ms intervals

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
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_rate_limiting(self, mock_collect_data, _mock_conn):
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

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_method_call_exception_handling(self, mock_collect_data, _mock_conn):
        """Test exception handling in method calls."""
        mock_collect_data.side_effect = Exception("Network error")

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Should propagate exception for single calls
        with pytest.raises(Exception) as exc_info:
            client.collect_data("2023-12-31", "123456")

        assert "Network error" in str(exc_info.value)

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_parallel_partial_failure_recovery(self, mock_collect_data, _mock_conn):
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


# ---------------------------------------------------------------------------
# Additional coverage tests for async_compatible.py
# ---------------------------------------------------------------------------


class TestCollectTimeSeries:
    """Tests for collect_time_series error handling (lines 279-280)."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_error_dict_when_future_raises(self, mock_collect_data, _mock_conn):
        """When future.result() raises, should return error dict (lines 279-280)."""

        def side_effect(conn, creds, period, rssd_id, *args):
            if period == "2023-09-30":
                raise Exception("Period unavailable")
            return [{"period": period, "data": "ok"}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        periods = ["2023-12-31", "2023-09-30"]
        results = client.collect_time_series("123456", periods)

        assert len(results) == 2
        assert "error" in results["2023-09-30"]
        assert "Period unavailable" in results["2023-09-30"]["error"]
        assert results["2023-09-30"]["period"] == "2023-09-30"
        # Successful period should be fine
        assert results["2023-12-31"][0]["period"] == "2023-12-31"


class TestAsyncCallbackHandling:
    """Tests for async callback handling (lines 369-372)."""

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_sync_callback_on_error(self, mock_collect_data, _mock_conn):
        """Sync callback should be called even on error (line 372)."""
        mock_collect_data.side_effect = Exception("Fetch failed")

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        progress_calls = []

        def sync_callback(rssd_id, result):
            progress_calls.append((rssd_id, result))

        rssd_ids = ["123456"]
        results = await client.collect_batch_async(
            "2023-12-31", rssd_ids, progress_callback=sync_callback
        )

        assert len(progress_calls) == 1
        assert "error" in progress_calls[0][1]
        assert "Fetch failed" in progress_calls[0][1]["error"]

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_callback_on_error(self, mock_collect_data, _mock_conn):
        """Async callback should be called on error (lines 369-370)."""
        mock_collect_data.side_effect = Exception("Async fetch failed")

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        progress_calls = []

        async def async_callback(rssd_id, result):
            progress_calls.append((rssd_id, result))

        rssd_ids = ["123456"]
        results = await client.collect_batch_async(
            "2023-12-31", rssd_ids, progress_callback=async_callback
        )

        assert len(progress_calls) == 1
        assert "error" in progress_calls[0][1]
        assert "Async fetch failed" in progress_calls[0][1]["error"]


class TestAsyncTimeSeriesError:
    """Tests for async time series error handling (lines 414-415)."""

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_error_in_async_time_series(self, mock_collect_data, _mock_conn):
        """Errors in collect_time_series_async should produce error dicts (lines 414-415)."""

        def side_effect(conn, creds, period, rssd_id, *args):
            if period == "2023-06-30":
                raise Exception("Server error")
            return [{"period": period, "data": "ok"}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        periods = ["2023-12-31", "2023-06-30"]
        results = await client.collect_time_series_async("123456", periods)

        assert len(results) == 2
        assert "error" in results["2023-06-30"]
        assert "Server error" in results["2023-06-30"]["error"]
        assert results["2023-06-30"]["period"] == "2023-06-30"


class TestExecutorShutdownInClose:
    """Tests for executor shutdown in close() (line 431)."""

    def test_owned_executor_shutdown_called(self):
        """close() should call executor.shutdown when client owns the executor (line 431/446)."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds)

        assert client._owned_executor is True
        mock_executor = Mock()
        client.executor = mock_executor

        client.close()

        mock_executor.shutdown.assert_called_once_with(wait=True)

    def test_non_owned_executor_not_shutdown(self):
        """close() should NOT call executor.shutdown when externally provided."""
        creds = Mock(spec=WebserviceCredentials)
        external_executor = Mock()
        client = AsyncCompatibleClient(creds, executor=external_executor)

        assert client._owned_executor is False

        client.close()

        external_executor.shutdown.assert_not_called()


class TestRESTClientBranches:
    """Tests for REST client branches in collect_data and collect_reporting_periods."""

    @patch("ffiec_data_connect.methods.collect_data")
    def test_collect_data_rest_client_passes_none_conn(self, mock_collect_data):
        """REST client should pass None as connection (line 127)."""
        from ffiec_data_connect.credentials import OAuth2Credentials

        TEST_JWT = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
        creds = OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)

        mock_collect_data.return_value = [{"test": "data"}]

        client = AsyncCompatibleClient(creds, rate_limit=None)
        result = client.collect_data("2023-12-31", "123456")

        # First arg should be None for REST client
        args = mock_collect_data.call_args[0]
        assert args[0] is None
        assert result == [{"test": "data"}]

    @patch("ffiec_data_connect.methods.collect_reporting_periods")
    def test_collect_reporting_periods_rest_client(self, mock_collect_periods):
        """REST client should pass None as connection (line 166/171)."""
        from ffiec_data_connect.credentials import OAuth2Credentials

        TEST_JWT = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
        creds = OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)

        mock_collect_periods.return_value = ["2023-12-31"]

        client = AsyncCompatibleClient(creds, rate_limit=None)
        result = client.collect_reporting_periods("call")

        args = mock_collect_periods.call_args[0]
        assert args[0] is None
        assert result == ["2023-12-31"]

    @patch("ffiec_data_connect.methods.collect_reporting_periods")
    def test_collect_reporting_periods_with_rate_limiter(self, mock_collect_periods):
        """Rate limiter should be applied in collect_reporting_periods (line 165)."""
        from ffiec_data_connect.credentials import OAuth2Credentials

        TEST_JWT = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzgzNDQyMjUzfQ."
        creds = OAuth2Credentials(username="testuser", bearer_token=TEST_JWT)

        mock_collect_periods.return_value = ["2023-12-31"]
        mock_limiter = Mock()

        client = AsyncCompatibleClient(creds, rate_limit=10)
        client.rate_limiter = mock_limiter

        client.collect_reporting_periods("call")

        mock_limiter.wait_if_needed.assert_called_once()


class TestProgressCallbackOnErrorInParallel:
    """Test progress_callback is called on error in collect_data_parallel (line 231)."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_progress_callback_called_on_error(self, mock_collect_data, _mock_conn):
        """When a future raises, progress_callback should be called with error dict (line 231)."""

        def side_effect(conn, creds, period, rssd_id, *args):
            if rssd_id == "111":
                raise Exception("Connection refused")
            return [{"rssd": rssd_id}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        progress_calls = []

        def progress_cb(rssd_id, result):
            progress_calls.append((rssd_id, result))

        results = client.collect_data_parallel(
            "2023-12-31",
            ["111", "222"],
            progress_callback=progress_cb,
        )

        # Both RSDs should trigger progress callbacks
        assert len(progress_calls) == 2
        rssd_ids_called = [c[0] for c in progress_calls]
        assert "111" in rssd_ids_called
        assert "222" in rssd_ids_called

        # The error callback should have an error key
        error_call = next(c for c in progress_calls if c[0] == "111")
        assert "error" in error_call[1]
        assert "Connection refused" in error_call[1]["error"]


class TestRateLimiterInTimeSeries:
    """Test rate_limiter.wait_if_needed is called in collect_time_series (line 262)."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_rate_limiter_called_in_time_series(self, mock_collect_data, _mock_conn):
        """Rate limiter should be called for each period in collect_time_series (line 262)."""
        mock_collect_data.return_value = [{"data": "ok"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=10)

        # Replace rate_limiter with a mock to verify calls
        mock_limiter = Mock()
        client.rate_limiter = mock_limiter

        periods = ["2023-12-31", "2023-09-30", "2023-06-30"]
        results = client.collect_time_series("123456", periods)

        assert len(results) == 3
        # Called once per period in collect_time_series + once per period in collect_data
        assert mock_limiter.wait_if_needed.call_count >= 3


class TestRateLimiterInBatchAsync:
    """Test rate_limiter in collect_batch_async (line 349)."""

    @pytest.mark.asyncio
    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    async def test_rate_limiter_called_in_batch_async(
        self, mock_collect_data, _mock_conn
    ):
        """Rate limiter should be called for each RSSD in collect_batch_async (line 349)."""
        mock_collect_data.return_value = [{"data": "ok"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=10)

        # Replace rate_limiter with a mock that has both sync and async methods
        mock_limiter = Mock()
        mock_limiter.async_wait_if_needed = AsyncMock()
        mock_limiter.wait_if_needed = Mock()
        client.rate_limiter = mock_limiter

        rssd_ids = ["111", "222"]
        results = await client.collect_batch_async("2023-12-31", rssd_ids)

        assert len(results) == 2
        # async_wait_if_needed is called both in collect_batch_async and collect_data_async
        assert mock_limiter.async_wait_if_needed.call_count >= 2


class TestExecutorShutdownOwnedReal:
    """Test executor shutdown in close() with a real owned executor (line 446)."""

    def test_close_shuts_down_real_owned_executor(self):
        """Create client without external executor, then close(). Executor should be shut down."""
        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        assert client._owned_executor is True
        executor = client.executor
        assert executor is not None

        # Close the client -- should shut down the executor
        client.close()

        # Verify the executor is shut down by trying to submit (should raise)
        import concurrent.futures

        with pytest.raises(RuntimeError):
            executor.submit(lambda: None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
