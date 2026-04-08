"""
Comprehensive memory leak detection test suite for FFIEC Data Connect.

Tests memory usage patterns, garbage collection behavior, resource cleanup,
and memory efficiency under various usage scenarios.
"""

import gc
import os
import threading
import time
import tracemalloc
import weakref
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest

from ffiec_data_connect import methods
from ffiec_data_connect.async_compatible import AsyncCompatibleClient, RateLimiter
from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.exceptions import SOAPDeprecationError
from ffiec_data_connect.ffiec_connection import FFIECConnection, ProxyProtocol


# Helper: patch _get_connection so it returns a Mock instead of calling FFIECConnection()
_patch_get_conn = patch.object(
    AsyncCompatibleClient, "_get_connection", return_value=Mock()
)


class MemoryTestBase:
    """Base class for memory leak testing utilities."""

    def measure_memory_usage(self, func, *args, **kwargs):
        """Measure memory usage of a function execution.

        Returns:
            Tuple of (result, peak_memory_bytes, memory_growth_bytes)
        """
        # Start memory tracing
        tracemalloc.start()
        gc.collect()  # Clean slate

        # Get initial memory
        start_memory = tracemalloc.get_traced_memory()[0]
        process = psutil.Process(os.getpid())
        start_rss = process.memory_info().rss

        # Execute function
        result = func(*args, **kwargs)

        # Measure peak and current memory
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        end_rss = process.memory_info().rss

        tracemalloc.stop()

        memory_growth = current_memory - start_memory
        rss_growth = end_rss - start_rss

        return result, peak_memory, memory_growth, rss_growth

    def create_memory_stress_test(self, factory_func, iterations: int = 100):
        """Create and destroy objects to test for memory leaks."""
        objects = []
        weak_refs = []

        # Create objects
        for i in range(iterations):
            obj = factory_func(i)
            objects.append(obj)
            weak_refs.append(weakref.ref(obj))

        # Clear references
        objects.clear()
        gc.collect()

        # Check if objects were properly collected
        alive_objects = sum(1 for ref in weak_refs if ref() is not None)
        return alive_objects, len(weak_refs)

    def monitor_memory_over_time(
        self, func, duration_seconds: float = 1.0, interval: float = 0.1
    ):
        """Monitor memory usage over time during function execution."""
        memory_samples = []
        process = psutil.Process(os.getpid())

        def memory_monitor():
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                memory_samples.append(process.memory_info().rss)
                time.sleep(interval)

        # Start monitoring
        monitor_thread = threading.Thread(target=memory_monitor)
        monitor_thread.start()

        # Execute function
        result = func()

        # Wait for monitoring to complete
        monitor_thread.join()

        return result, memory_samples


class TestCredentialsMemoryLeaks(MemoryTestBase):
    """Test memory leaks in credentials module.

    Note: WebserviceCredentials now raises SOAPDeprecationError on instantiation.
    These tests verify that behavior and use Mock objects where credential-like
    objects are needed.
    """

    def test_webservice_credentials_raises_soap_deprecation(self):
        """Test that WebserviceCredentials raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            WebserviceCredentials("user", "pass")

    def test_mock_credential_object_cleanup(self):
        """Test that mock credential objects are properly garbage collected."""

        def create_credential(i):
            mock = Mock(spec=WebserviceCredentials)
            mock.username = f"user_{i}"
            mock.password = f"pass_{i}"
            return mock

        alive, total = self.create_memory_stress_test(create_credential, 500)

        # Most credential objects should be garbage collected (allow < 1% to remain due to GC timing)
        max_alive = max(1, total // 100)  # Allow up to 1% or at least 1
        assert (
            alive <= max_alive
        ), f"{alive} out of {total} credential objects not garbage collected"

    def test_mock_credential_memory_after_gc(self):
        """Test that mock credentials release memory after garbage collection."""
        initial_memory = (
            tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        )

        # Create many mock credentials
        credentials = []
        tracemalloc.start()

        for i in range(200):
            creds = Mock(spec=WebserviceCredentials)
            creds.username = f"user_{i}"
            creds.password = f"password_{i}"
            credentials.append(creds)

        memory_with_objects = tracemalloc.get_traced_memory()[0]

        # Clear and collect
        credentials.clear()
        gc.collect()

        memory_after_gc = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        # Should have released most memory
        memory_retained = memory_after_gc - initial_memory
        memory_used = memory_with_objects - initial_memory

        # Should retain less than 10% of peak memory
        assert (
            memory_retained < memory_used * 0.1
        ), f"Too much memory retained: {memory_retained} bytes"


class TestFFIECConnectionMemoryLeaks(MemoryTestBase):
    """Test memory leaks in FFIEC connection management.

    Note: FFIECConnection now raises SOAPDeprecationError on instantiation.
    """

    def test_connection_raises_soap_deprecation(self):
        """Test that FFIECConnection raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            FFIECConnection()


class TestAsyncCompatibleClientMemoryLeaks(MemoryTestBase):
    """Test memory leaks in async compatible client."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_client_data_collection_memory(self, mock_collect_data, _mock_conn):
        """Test memory usage during data collection operations."""
        mock_collect_data.return_value = [{"test": "data"}]

        def perform_data_collections():
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, rate_limit=None)

            results = []
            for i in range(100):
                result = client.collect_data("2023-12-31", f"12345{i}")
                results.append(result)

            client.close()
            return results

        result, peak, growth, rss_growth = self.measure_memory_usage(
            perform_data_collections
        )

        # Data collection should be memory efficient
        max_expected_growth = 100 * 5000  # 500KB allowance
        assert (
            growth < max_expected_growth
        ), f"Data collection memory inefficient: {growth} bytes"

    def test_connection_cache_memory_management(self):
        """Test memory management of connection caching."""

        def test_connection_caching():
            creds = Mock(spec=WebserviceCredentials)
            clients = []

            # Create clients with mock connections injected into cache
            for i in range(20):
                client = AsyncCompatibleClient(creds)
                # Inject mock connection instead of calling _get_connection()
                client._connection_cache[threading.get_ident() + i] = Mock()
                clients.append(client)

            # Close all clients
            for client in clients:
                client.close()

            return len(clients)

        result, peak, growth, rss_growth = self.measure_memory_usage(
            test_connection_caching
        )

        # Connection caching should cleanup properly
        max_expected_growth = 20 * 25000  # 500KB allowance (mock + executor overhead)
        assert (
            growth < max_expected_growth
        ), f"Connection cache memory leak: {growth} bytes"

    def test_rate_limiter_memory_stability(self):
        """Test rate limiter memory usage over time."""
        rate_limiter = RateLimiter(calls_per_second=100)

        def stress_rate_limiter():
            for _ in range(1000):
                rate_limiter.wait_if_needed()

        result, peak, growth, rss_growth = self.measure_memory_usage(
            stress_rate_limiter
        )

        # Rate limiter should use constant memory
        max_expected_growth = 10000  # 10KB allowance
        assert (
            growth < max_expected_growth
        ), f"Rate limiter memory growth: {growth} bytes"

    def test_client_garbage_collection(self):
        """Test that clients are properly garbage collected."""

        def create_client(i):
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds)
            # Inject mock connection instead of calling _get_connection()
            client._connection_cache[i] = Mock()
            client.close()
            return client

        alive, total = self.create_memory_stress_test(create_client, 50)

        # Most clients should be garbage collected after closing (allow up to 10% due to executor cleanup timing)
        max_alive = max(2, total // 10)  # Allow up to 10% or at least 2
        assert (
            alive <= max_alive
        ), f"{alive} out of {total} clients not garbage collected"

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_parallel_processing_memory(self, mock_collect_data, _mock_conn):
        """Test memory usage during parallel processing."""
        mock_collect_data.return_value = [{"test": "data"}]

        def parallel_data_collection():
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, max_concurrent=5, rate_limit=None)

            rssd_ids = [f"12345{i}" for i in range(50)]
            results = client.collect_data_parallel("2023-12-31", rssd_ids)

            client.close()
            return results

        result, peak, growth, rss_growth = self.measure_memory_usage(
            parallel_data_collection
        )

        # Parallel processing should manage memory efficiently
        max_expected_growth = 50 * 8000  # 400KB allowance
        assert (
            growth < max_expected_growth
        ), f"Parallel processing memory inefficient: {growth} bytes"


class TestMethodsMemoryLeaks(MemoryTestBase):
    """Test memory leaks in methods module."""

    def test_validation_function_memory_stability(self):
        """Test memory stability of validation functions."""
        from ffiec_data_connect.methods import (
            _date_format_validator,
            _output_type_validator,
            _validate_rssd_id,
        )

        def stress_test_validators():
            for i in range(1000):
                # Test different validation functions
                _validate_rssd_id(f"12345{i}")
                _date_format_validator("string_original")
                _output_type_validator("list")

        result, peak, growth, rss_growth = self.measure_memory_usage(
            stress_test_validators
        )

        # Validation functions should use minimal memory
        max_expected_growth = 50000  # 50KB allowance
        assert (
            growth < max_expected_growth
        ), f"Validation functions memory growth: {growth} bytes"

    def test_date_utility_memory_efficiency(self):
        """Test memory efficiency of date utility functions."""
        from datetime import datetime

        from ffiec_data_connect.methods import (
            _convert_any_date_to_ffiec_format,
            _create_ffiec_date_from_datetime,
            _is_valid_date_or_quarter,
        )

        def stress_test_date_utilities():
            test_date = datetime(2023, 12, 31)
            results = []

            for i in range(500):
                results.append(_convert_any_date_to_ffiec_format("2023-12-31"))
                results.append(_create_ffiec_date_from_datetime(test_date))
                results.append(_is_valid_date_or_quarter(test_date))

            return results

        result, peak, growth, rss_growth = self.measure_memory_usage(
            stress_test_date_utilities
        )

        # Date utilities should be memory efficient
        max_expected_growth = 500 * 500  # 250KB allowance
        assert (
            growth < max_expected_growth
        ), f"Date utilities memory inefficient: {growth} bytes"


class TestIntegrationMemoryLeaks(MemoryTestBase):
    """Test memory leaks in integration scenarios."""

    @_patch_get_conn
    @patch("ffiec_data_connect.methods.collect_data")
    def test_full_workflow_memory_stability(self, mock_collect_data, _mock_conn):
        """Test memory stability during full workflow simulation."""
        mock_collect_data.return_value = [
            {"test": "data", "size": "x" * 1000}
        ]  # 1KB per result

        def simulate_full_workflow():
            # Simulate real usage pattern with mock credentials
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, max_concurrent=3, rate_limit=None)

            results = []

            # Multiple data collection rounds
            for round_num in range(5):
                # Collect data for multiple banks
                rssd_ids = [f"1234{i}" for i in range(10)]
                round_results = client.collect_data_parallel(
                    f"2023-0{round_num+1}-31", rssd_ids
                )
                results.append(round_results)

                # Time series for one bank
                periods = [f"2023-0{i}-31" for i in range(1, 4)]
                time_series = client.collect_time_series("123456", periods)
                results.append(time_series)

            client.close()
            return results

        result, peak, growth, rss_growth = self.measure_memory_usage(
            simulate_full_workflow
        )

        # Full workflow should be memory efficient
        # 5 rounds * (10 banks + 3 periods) * 1KB + overhead
        max_expected_growth = 5 * 13 * 2000 + 200000  # ~330KB allowance
        assert (
            growth < max_expected_growth
        ), f"Full workflow memory inefficient: {growth} bytes"

    def test_long_running_session_memory(self):
        """Test memory behavior in long-running sessions."""

        def simulate_long_running_session():
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, rate_limit=None)

            # Simulate keeping client alive and using it repeatedly
            memory_samples = []
            process = psutil.Process(os.getpid())

            for i in range(20):
                # Do some work (inject mock connections instead of calling _get_connection)
                client._connection_cache[i] = Mock()

                # Sample memory
                memory_samples.append(process.memory_info().rss)

                if i % 5 == 0:
                    # Periodic cleanup simulation
                    gc.collect()

            client.close()
            return memory_samples

        result, peak, growth, rss_growth = self.measure_memory_usage(
            simulate_long_running_session
        )

        # Memory should be stable in long-running sessions
        memory_samples = result
        if len(memory_samples) >= 2:
            memory_growth_over_time = memory_samples[-1] - memory_samples[0]
            max_allowed_growth = 50 * 1024 * 1024  # 50MB
            assert (
                memory_growth_over_time < max_allowed_growth
            ), f"Long-running session memory growth: {memory_growth_over_time} bytes"

    @_patch_get_conn
    def test_exception_handling_memory_cleanup(self, _mock_conn):
        """Test that exceptions don't cause memory leaks."""

        @patch("ffiec_data_connect.methods.collect_data")
        def test_with_exceptions(mock_collect_data):
            mock_collect_data.side_effect = Exception("Simulated error")

            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds, rate_limit=None)

            # Try operations that will fail
            for i in range(50):
                try:
                    client.collect_data("2023-12-31", f"12345{i}")
                except Exception:
                    pass  # Expected

            client.close()

        result, peak, growth, rss_growth = self.measure_memory_usage(
            test_with_exceptions
        )

        # Exception handling shouldn't leak memory
        max_expected_growth = (
            50 * 8000
        )  # 400KB allowance (exceptions have stack trace overhead + mock overhead)
        assert (
            growth < max_expected_growth
        ), f"Exception handling leaked memory: {growth} bytes"


class TestMemoryPressureScenarios(MemoryTestBase):
    """Test behavior under memory pressure scenarios."""

    def test_high_volume_object_creation(self):
        """Test memory behavior with high volume object creation."""

        def create_high_volume_objects():
            objects = []

            # Create many objects rapidly using mocks (since real constructors raise)
            for i in range(1000):
                creds = Mock(spec=WebserviceCredentials)
                conn = Mock(spec=FFIECConnection)
                client = AsyncCompatibleClient(creds)

                objects.append((creds, conn, client))

                # Periodic cleanup
                if i % 100 == 0:
                    # Clean up some old objects
                    for j in range(min(10, len(objects))):
                        _, _, old_client = objects[j]
                        old_client.close()

            # Final cleanup
            for _, _, client in objects:
                client.close()

            return len(objects)

        result, peak, growth, rss_growth = self.measure_memory_usage(
            create_high_volume_objects
        )

        # High volume creation should manage memory reasonably
        max_expected_growth = 1000 * 15000  # 15MB allowance (Mock objects are heavier)
        assert (
            growth < max_expected_growth
        ), f"High volume creation memory issue: {growth} bytes"

    def test_memory_cleanup_under_gc_pressure(self):
        """Test memory cleanup behavior when garbage collector is under pressure."""

        def create_gc_pressure():
            # Create pressure that should trigger garbage collection
            large_objects = []

            for i in range(100):
                # Create large object to pressure GC
                large_data = [f"data_{j}" * 100 for j in range(100)]  # ~10KB per object
                large_objects.append(large_data)

                # Create FFIEC objects using mocks
                creds = Mock(spec=WebserviceCredentials)
                conn = Mock(spec=FFIECConnection)
                client = AsyncCompatibleClient(creds)

                # Use and cleanup immediately
                client._connection_cache[i] = Mock()
                client.close()

                # Force GC periodically
                if i % 20 == 0:
                    gc.collect()

            # Clear large objects
            large_objects.clear()
            gc.collect()

        result, peak, growth, rss_growth = self.measure_memory_usage(create_gc_pressure)

        # Should handle GC pressure gracefully
        max_expected_growth = 100 * 15000  # 1.5MB allowance
        assert (
            growth < max_expected_growth
        ), f"GC pressure handling issue: {growth} bytes"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
