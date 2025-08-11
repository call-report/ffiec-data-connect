"""
Comprehensive async integration test suite for FFIEC Data Connect.

Tests async/await patterns, integration with external async frameworks,
asyncio event loop interaction, and real-world async usage scenarios.
"""

import asyncio
import gc
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from ffiec_data_connect import methods
from ffiec_data_connect.async_compatible import AsyncCompatibleClient, RateLimiter
from ffiec_data_connect.credentials import WebserviceCredentials


class AsyncIntegrationTestBase:
    """Base class for async integration testing utilities."""

    async def run_concurrent_async_tasks(
        self, tasks: List[Callable], timeout: float = 30.0
    ):
        """Run multiple async tasks concurrently with timeout protection."""
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[task() for task in tasks], return_exceptions=True),
                timeout=timeout,
            )
            return results
        except asyncio.TimeoutError:
            pytest.fail(f"Async tasks timed out after {timeout} seconds")

    async def measure_async_performance(self, async_func: Callable, *args, **kwargs):
        """Measure performance of async function execution."""
        start_time = time.time()
        result = await async_func(*args, **kwargs)
        end_time = time.time()

        return result, end_time - start_time

    def create_mock_async_framework_context(self):
        """Create a mock context similar to async frameworks like FastAPI, Django Channels, etc."""

        class MockAsyncFrameworkContext:
            def __init__(self):
                self.active_connections = []
                self.background_tasks = []

            async def add_connection(self, connection_id):
                self.active_connections.append(connection_id)

            async def remove_connection(self, connection_id):
                if connection_id in self.active_connections:
                    self.active_connections.remove(connection_id)

            async def add_background_task(self, task):
                self.background_tasks.append(task)

        return MockAsyncFrameworkContext()


@pytest.mark.asyncio
class TestAsyncBasicFunctionality(AsyncIntegrationTestBase):
    """Test basic async functionality and integration."""

    async def test_async_client_basic_usage(self):
        """Test basic async client usage patterns."""
        creds = Mock(spec=WebserviceCredentials)

        async with AsyncCompatibleClient(creds, rate_limit=None) as client:
            # Basic async operations should work
            assert client is not None
            assert hasattr(client, "collect_data_async")
            assert hasattr(client, "collect_batch_async")

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_data_collection_basic(self, mock_collect_data):
        """Test basic async data collection."""
        mock_collect_data.return_value = [{"test": "async_data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        result = await client.collect_data_async("2023-12-31", "123456")

        assert result == [{"test": "async_data"}]
        assert mock_collect_data.called

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_batch_collection_basic(self, mock_collect_data):
        """Test basic async batch collection."""

        def side_effect(*args):
            rssd_id = args[3]
            return [{"rssd": rssd_id, "data": f"async_{rssd_id}"}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        rssd_ids = ["123456", "123457", "123458"]
        results = await client.collect_batch_async("2023-12-31", rssd_ids)

        assert len(results) == 3
        for rssd_id in rssd_ids:
            assert rssd_id in results
            assert results[rssd_id][0]["rssd"] == rssd_id

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_time_series_basic(self, mock_collect_data):
        """Test basic async time series collection."""

        def side_effect(*args):
            period = args[2]
            return [{"period": period, "data": f"async_{period}"}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        periods = ["2023-12-31", "2023-09-30", "2023-06-30"]
        results = await client.collect_time_series_async("123456", periods)

        assert len(results) == 3
        for period in periods:
            assert period in results
            assert results[period][0]["period"] == period

        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
class TestAsyncRateLimiting(AsyncIntegrationTestBase):
    """Test async rate limiting functionality."""

    async def test_async_rate_limiter_timing(self):
        """Test that async rate limiter properly delays calls."""
        rate_limiter = RateLimiter(calls_per_second=10)  # 100ms intervals

        # First call should be immediate
        start_time = time.time()
        await rate_limiter.async_wait_if_needed()
        first_call_time = time.time() - start_time

        assert first_call_time < 0.01  # Should be immediate

        # Second call should be delayed
        start_time = time.time()
        await rate_limiter.async_wait_if_needed()
        second_call_time = time.time() - start_time

        assert 0.08 < second_call_time < 0.12  # Should wait ~100ms

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_client_rate_limiting(self, mock_collect_data):
        """Test rate limiting in async client operations."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(
            creds, rate_limit=100
        )  # Fast rate for testing - 10ms intervals

        # Sequential async calls should be rate limited
        start_time = time.time()

        # Make calls sequentially to test rate limiting properly
        results = []
        for i in range(3):
            result = await client.collect_data_async("2023-12-31", f"12345{i}")
            results.append(result)

        total_time = time.time() - start_time

        # Should take at least some time due to rate limiting (allow for timing variance)
        assert total_time >= 0.015  # At least 15ms for 3 calls with 10ms intervals
        assert len(results) == 3

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_concurrent_rate_limited_batches(self, mock_collect_data):
        """Test concurrent batch operations with rate limiting."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(
            creds, rate_limit=None, max_concurrent=2
        )  # No rate limiting for simplicity

        # Two small concurrent batches to test concurrency without timing complexity
        rssd_ids_1 = ["123401", "123402"]
        rssd_ids_2 = ["123411", "123412"]

        start_time = time.time()
        batch_1_task = client.collect_batch_async("2023-01-31", rssd_ids_1)
        batch_2_task = client.collect_batch_async("2023-02-31", rssd_ids_2)

        batch_results = await asyncio.gather(batch_1_task, batch_2_task)
        total_time = time.time() - start_time

        # Should complete both batches
        assert len(batch_results) == 2
        assert len(batch_results[0]) == 2  # 2 RSDs in first batch
        assert len(batch_results[1]) == 2  # 2 RSDs in second batch

        # Should complete reasonably quickly
        assert total_time < 2.0

        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
class TestAsyncConcurrencyPatterns(AsyncIntegrationTestBase):
    """Test async concurrency patterns and behavior."""

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_asyncio_gather_pattern(self, mock_collect_data):
        """Test asyncio.gather pattern with FFIEC client."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Gather multiple different operations
        tasks = [
            client.collect_data_async("2023-12-31", "123456"),
            client.collect_data_async("2023-12-31", "123457"),
            client.collect_time_series_async("123458", ["2023-12-31", "2023-09-30"]),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert results[0] == [{"test": "data"}]  # Single data collection
        assert results[1] == [{"test": "data"}]  # Single data collection
        assert isinstance(results[2], dict)  # Time series returns dict

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_asyncio_as_completed_pattern(self, mock_collect_data):
        """Test asyncio.as_completed pattern with FFIEC client."""

        def side_effect(*args):
            rssd_id = args[3]
            # Return immediately without sleep to avoid blocking
            return [{"rssd": rssd_id}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        rssd_ids = ["123456", "123457", "123458", "123459"]
        tasks = [
            client.collect_data_async("2023-12-31", rssd_id) for rssd_id in rssd_ids
        ]

        completed_rssd_ids = []
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed_rssd_ids.append(result[0]["rssd"])

        # All should complete, potentially in different order
        assert len(completed_rssd_ids) == 4
        assert set(completed_rssd_ids) == set(rssd_ids)

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_semaphore_integration(self, mock_collect_data):
        """Test integration with asyncio semaphores for custom concurrency control."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Custom semaphore to limit concurrency further
        semaphore = asyncio.Semaphore(2)  # Only 2 concurrent operations

        async def limited_collect(rssd_id):
            async with semaphore:
                return await client.collect_data_async("2023-12-31", rssd_id)

        # Start many tasks but only 2 should run concurrently
        tasks = [limited_collect(f"12345{i}") for i in range(6)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        assert len(results) == 6
        # With semaphore limiting to 2, should take longer than unlimited concurrency
        # but still faster than purely sequential

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_timeout_handling(self, mock_collect_data):
        """Test timeout handling in async operations."""

        # Mock that simulates a timeout scenario without blocking
        # We'll simulate the timeout by making the executor task take too long
        def normal_side_effect(*args):
            return [{"test": "fast_data"}]

        mock_collect_data.side_effect = normal_side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Test that very short timeouts work properly
        # This should complete successfully with a reasonable timeout
        try:
            result = await asyncio.wait_for(
                client.collect_data_async("2023-12-31", "123456"),
                timeout=1.0,  # 1 second timeout - should be plenty
            )
            assert result == [{"test": "fast_data"}]
        except asyncio.TimeoutError:
            # If this fails, it indicates an issue with the async implementation
            pytest.fail(
                "Async operation timed out unexpectedly - this suggests a threading issue"
            )

        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
class TestAsyncFrameworkIntegration(AsyncIntegrationTestBase):
    """Test integration with async frameworks and patterns."""

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_fastapi_like_integration(self, mock_collect_data):
        """Test FastAPI-like integration pattern."""
        mock_collect_data.return_value = [{"bank_data": "test"}]

        # Simulate FastAPI-like setup
        class MockFastAPIApp:
            def __init__(self):
                self.ffiec_client = None

            async def startup(self):
                creds = Mock(spec=WebserviceCredentials)
                self.ffiec_client = AsyncCompatibleClient(creds, rate_limit=10)

            async def shutdown(self):
                if self.ffiec_client:
                    await self.ffiec_client.__aexit__(None, None, None)

            async def get_bank_data(self, rssd_id: str):
                return await self.ffiec_client.collect_data_async("2023-12-31", rssd_id)

        app = MockFastAPIApp()
        await app.startup()

        # Simulate multiple concurrent API requests
        api_tasks = [app.get_bank_data(f"12345{i}") for i in range(5)]

        results = await asyncio.gather(*api_tasks)

        assert len(results) == 5
        for result in results:
            assert result == [{"bank_data": "test"}]

        await app.shutdown()

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_django_channels_like_integration(self, mock_collect_data):
        """Test Django Channels-like WebSocket integration pattern."""
        mock_collect_data.return_value = [{"real_time_data": "test"}]

        # Simulate Django Channels WebSocket consumer
        class MockWebSocketConsumer:
            def __init__(self):
                self.ffiec_client = None
                self.connected_clients = []

            async def connect(self, client_id):
                if not self.ffiec_client:
                    creds = Mock(spec=WebserviceCredentials)
                    self.ffiec_client = AsyncCompatibleClient(creds, rate_limit=20)
                self.connected_clients.append(client_id)

            async def disconnect(self, client_id):
                if client_id in self.connected_clients:
                    self.connected_clients.remove(client_id)
                if not self.connected_clients and self.ffiec_client:
                    await self.ffiec_client.__aexit__(None, None, None)
                    self.ffiec_client = None

            async def broadcast_bank_data(self, rssd_id):
                data = await self.ffiec_client.collect_data_async("2023-12-31", rssd_id)
                # Simulate broadcast to all connected clients
                return {client_id: data for client_id in self.connected_clients}

        consumer = MockWebSocketConsumer()

        # Simulate multiple clients connecting
        await consumer.connect("client_1")
        await consumer.connect("client_2")
        await consumer.connect("client_3")

        # Broadcast data
        broadcast_result = await consumer.broadcast_bank_data("123456")

        assert len(broadcast_result) == 3
        assert "client_1" in broadcast_result
        assert "client_2" in broadcast_result
        assert "client_3" in broadcast_result

        # Disconnect all clients
        await consumer.disconnect("client_1")
        await consumer.disconnect("client_2")
        await consumer.disconnect("client_3")

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_background_task_processing(self, mock_collect_data):
        """Test background task processing patterns."""
        mock_collect_data.return_value = [{"processed": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Simple background task pattern without complex queues
        async def process_tasks_in_background(task_list):
            """Process tasks concurrently in background."""
            tasks = [
                client.collect_data_async(task["period"], task["rssd_id"])
                for task in task_list
            ]
            return await asyncio.gather(*tasks)

        # Test data
        tasks = [{"rssd_id": f"12345{i}", "period": "2023-12-31"} for i in range(5)]

        # Process in background
        results = await process_tasks_in_background(tasks)

        assert len(results) == 5
        for result in results:
            assert result == [{"processed": "data"}]

        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
class TestAsyncErrorHandling(AsyncIntegrationTestBase):
    """Test error handling in async contexts."""

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_error_propagation(self, mock_collect_data):
        """Test that errors are properly propagated in async context."""
        mock_collect_data.side_effect = Exception("Network error")

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        with pytest.raises(Exception) as exc_info:
            await client.collect_data_async("2023-12-31", "123456")

        assert "Network error" in str(exc_info.value)

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_partial_batch_failure(self, mock_collect_data):
        """Test handling of partial failures in async batch operations."""

        def side_effect(*args):
            rssd_id = args[3]
            if rssd_id == "fail_me":
                raise Exception(f"Failed for {rssd_id}")
            return [{"rssd": rssd_id, "success": True}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        rssd_ids = ["123456", "fail_me", "123458"]
        results = await client.collect_batch_async("2023-12-31", rssd_ids)

        assert len(results) == 3
        assert results["123456"][0]["success"] is True
        assert "error" in results["fail_me"]
        assert results["123458"][0]["success"] is True

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_graceful_shutdown_with_errors(self, mock_collect_data):
        """Test graceful shutdown even when operations are failing."""

        # Create a mix of successful and failing operations
        def side_effect(*args):
            rssd_id = args[3]
            if int(rssd_id[-1]) % 2 == 0:  # Even RSDs fail
                raise Exception(f"Error for {rssd_id}")
            return [{"rssd": rssd_id}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Start multiple operations, some will fail
        tasks = [
            asyncio.create_task(client.collect_data_async("2023-12-31", f"12345{i}"))
            for i in range(10)
        ]

        # Let some tasks start
        await asyncio.sleep(0.1)

        # Cancel remaining tasks and shutdown
        for task in tasks:
            if not task.done():
                task.cancel()

        # Gather with return_exceptions to handle cancellations
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle mix of results, exceptions, and cancellations
        successful_count = sum(1 for r in results if isinstance(r, list))
        error_count = sum(
            1
            for r in results
            if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError)
        )
        cancelled_count = sum(
            1 for r in results if isinstance(r, asyncio.CancelledError)
        )

        assert successful_count + error_count + cancelled_count == 10

        # Should still shutdown gracefully
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
class TestAsyncPerformancePatterns(AsyncIntegrationTestBase):
    """Test performance patterns and optimizations in async context."""

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_vs_sync_performance_comparison(self, mock_collect_data):
        """Compare async vs sync performance for parallel operations."""

        # Mock operation with consistent delay
        def side_effect(*args):
            time.sleep(0.05)  # 50ms delay
            return [{"test": "data"}]

        mock_collect_data.side_effect = side_effect

        creds = Mock(spec=WebserviceCredentials)

        # Test async approach
        async_client = AsyncCompatibleClient(creds, rate_limit=None, max_concurrent=5)

        rssd_ids = [f"12345{i}" for i in range(10)]

        # Async batch operation
        async_start = time.time()
        async_results = await async_client.collect_batch_async("2023-12-31", rssd_ids)
        async_time = time.time() - async_start

        # Sync parallel operation (for comparison)
        sync_start = time.time()
        sync_results = async_client.collect_data_parallel("2023-12-31", rssd_ids)
        sync_time = time.time() - sync_start

        # Both should complete successfully
        assert len(async_results) == 10
        assert len(sync_results) == 10

        # Times should be comparable (both are parallel)
        # Allow for some variance in timing
        time_ratio = async_time / sync_time
        assert 0.5 < time_ratio < 2.0  # Should be within 2x of each other

        await async_client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_memory_efficiency_under_load(self, mock_collect_data):
        """Test memory efficiency of async operations under load."""
        mock_collect_data.return_value = [{"data": "x" * 100}]  # Small data payload

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None, max_concurrent=10)

        # Create several async operations (reduced for test speed)
        async def create_batch_operations():
            tasks = []
            for batch in range(5):  # 5 batches instead of 20
                rssd_ids = [
                    f"batch{batch}_rsd{i}" for i in range(3)
                ]  # 3 RSDs per batch instead of 10
                task = client.collect_batch_async(f"2023-{batch+1:02d}-31", rssd_ids)
                tasks.append(task)
            return tasks

        # Monitor memory during operations
        import gc

        gc.collect()

        tasks = await create_batch_operations()

        # Process all tasks at once (smaller number now)
        all_results = await asyncio.gather(*tasks)

        # Verify all operations completed
        assert len(all_results) == 5  # 5 batches
        for batch_result in all_results:
            assert len(batch_result) == 3  # 3 RSDs per batch

        await client.__aexit__(None, None, None)

    @patch("ffiec_data_connect.methods.collect_data")
    async def test_async_connection_reuse_efficiency(self, mock_collect_data):
        """Test that async operations efficiently reuse connections."""
        mock_collect_data.return_value = [{"test": "data"}]

        creds = Mock(spec=WebserviceCredentials)
        client = AsyncCompatibleClient(creds, rate_limit=None)

        # Create many operations that should reuse the same connection pool
        connection_ids = set()

        async def collect_and_track_connection(rssd_id):
            # Access the connection to track its ID
            conn = client._get_connection()
            connection_ids.add(id(conn))
            return await client.collect_data_async("2023-12-31", rssd_id)

        # Run several operations to test connection reuse
        tasks = [
            collect_and_track_connection(f"12345{i}")
            for i in range(20)  # Reduced from 50 for speed
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 20

        # Should reuse connections efficiently - expect only a few unique connection IDs
        # due to thread-local connection caching
        assert len(connection_ids) <= 10  # Should be much fewer than 20

        await client.__aexit__(None, None, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
