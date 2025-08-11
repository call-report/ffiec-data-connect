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
from ffiec_data_connect.ffiec_connection import FFIECConnection, ProxyProtocol


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
    """Test memory leaks in credentials module."""

    def test_credential_object_cleanup(self):
        """Test that credential objects are properly garbage collected."""

        def create_credential(i):
            return WebserviceCredentials(f"user_{i}", f"pass_{i}")

        alive, total = self.create_memory_stress_test(create_credential, 500)

        # Most credential objects should be garbage collected (allow < 1% to remain due to GC timing)
        max_alive = max(1, total // 100)  # Allow up to 1% or at least 1
        assert (
            alive <= max_alive
        ), f"{alive} out of {total} credential objects not garbage collected"

    def test_credential_string_interning(self):
        """Test memory efficiency of credential string handling."""
        # Test with many identical credentials (should benefit from string interning)
        result, peak, growth, rss_growth = self.measure_memory_usage(
            lambda: [
                WebserviceCredentials("same_user", "same_pass") for _ in range(1000)
            ]
        )

        # Memory growth should be reasonable despite 1000 objects
        # Each credential pair is ~100-200 bytes + overhead
        max_expected_growth = 1000 * 1000  # 1MB allowance
        assert growth < max_expected_growth, f"Excessive memory growth: {growth} bytes"

    def test_credential_memory_after_gc(self):
        """Test that credentials release memory after garbage collection."""
        initial_memory = (
            tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
        )

        # Create many credentials
        credentials = []
        tracemalloc.start()

        for i in range(200):
            creds = WebserviceCredentials(f"user_{i}", f"password_{i}")
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

    def test_environment_credential_caching_memory(self):
        """Test memory usage of environment credential caching."""
        with patch.dict(
            "os.environ", {"FFIEC_USERNAME": "env_user", "FFIEC_PASSWORD": "env_pass"}
        ):

            def create_env_credentials():
                return [WebserviceCredentials() for _ in range(100)]

            result, peak, growth, rss_growth = self.measure_memory_usage(
                create_env_credentials
            )

            # Environment credentials should be efficiently cached
            # Growth should be minimal since all use same env values
            max_expected_growth = 100 * 500  # 50KB allowance
            assert (
                growth < max_expected_growth
            ), f"Inefficient env credential memory: {growth} bytes"


class TestFFIECConnectionMemoryLeaks(MemoryTestBase):
    """Test memory leaks in FFIEC connection management."""

    def test_connection_cleanup_on_close(self):
        """Test that connections properly cleanup memory when closed."""

        def create_and_close_connection(i):
            conn = FFIECConnection()
            # Access session to ensure it's created
            _ = conn.session
            conn.close()
            return conn

        result, peak, growth, rss_growth = self.measure_memory_usage(
            lambda: [create_and_close_connection(i) for i in range(50)]
        )

        # After closing, memory growth should be minimal
        max_expected_growth = 50 * 2000  # 100KB allowance for 50 connections
        assert (
            growth < max_expected_growth
        ), f"Connection cleanup leaked memory: {growth} bytes"

    def test_session_caching_memory_efficiency(self):
        """Test that session caching doesn't cause memory leaks."""
        connections = []

        def create_connections_with_sessions():
            for i in range(20):
                conn = FFIECConnection()
                # Access session multiple times to test caching
                for _ in range(5):
                    _ = conn.session
                connections.append(conn)

        result, peak, growth, rss_growth = self.measure_memory_usage(
            create_connections_with_sessions
        )

        # Clean up
        for conn in connections:
            conn.close()
        connections.clear()
        gc.collect()

        # Session caching should be memory efficient
        max_expected_growth = 20 * 10000  # 200KB allowance (sessions have overhead)
        assert (
            growth < max_expected_growth
        ), f"Session caching memory inefficient: {growth} bytes"

    def test_proxy_configuration_memory_stability(self):
        """Test memory stability during proxy reconfiguration."""
        conn = FFIECConnection()

        def reconfigure_proxy_many_times():
            for i in range(100):
                conn.proxy_host = f"proxy{i}.example.com"
                conn.proxy_port = 8080 + i
                conn.proxy_protocol = ProxyProtocol.HTTP  # Set required protocol
                # Only enable proxy when configuration is complete
                if i % 2 == 0:
                    conn.use_proxy = True
                else:
                    conn.use_proxy = False
                # Trigger potential session regeneration
                try:
                    _ = conn.session
                except Exception:
                    pass  # Ignore any other errors

        result, peak, growth, rss_growth = self.measure_memory_usage(
            reconfigure_proxy_many_times
        )

        conn.close()

        # Proxy reconfigurations shouldn't leak memory
        max_expected_growth = 100 * 2000  # 200KB allowance (proxy configs + sessions)
        assert (
            growth < max_expected_growth
        ), f"Proxy reconfiguration leaked memory: {growth} bytes"

    def test_connection_garbage_collection(self):
        """Test that connection objects are properly garbage collected."""

        def create_connection(i):
            conn = FFIECConnection()
            _ = conn.session  # Create session
            return conn

        alive, total = self.create_memory_stress_test(create_connection, 100)

        # Most connections should be garbage collected (allow up to 5% due to session cleanup timing)
        max_alive = max(5, total // 20)  # Allow up to 5% or at least 5
        assert (
            alive <= max_alive
        ), f"{alive} out of {total} connections not garbage collected"

    def test_session_regeneration_memory_leak(self):
        """Test for memory leaks during session regeneration."""
        conn = FFIECConnection()

        def force_session_regenerations():
            sessions = []
            for i in range(50):
                # Force session creation
                session = conn.session
                sessions.append(id(session))

                # Force regeneration by changing config
                conn.proxy_host = f"host{i}.com"
                conn._config_hash = None

        result, peak, growth, rss_growth = self.measure_memory_usage(
            force_session_regenerations
        )

        conn.close()

        # Session regenerations shouldn't accumulate memory
        max_expected_growth = 50 * 2000  # 100KB allowance
        assert (
            growth < max_expected_growth
        ), f"Session regeneration leaked memory: {growth} bytes"


class TestAsyncCompatibleClientMemoryLeaks(MemoryTestBase):
    """Test memory leaks in async compatible client."""

    @patch("ffiec_data_connect.methods.collect_data")
    def test_client_data_collection_memory(self, mock_collect_data):
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

            # Create clients that will cache connections
            for i in range(20):
                client = AsyncCompatibleClient(creds)
                # Force connection creation
                _ = client._get_connection()
                clients.append(client)

            # Close all clients
            for client in clients:
                client.close()

            return len(clients)

        result, peak, growth, rss_growth = self.measure_memory_usage(
            test_connection_caching
        )

        # Connection caching should cleanup properly
        max_expected_growth = 20 * 3000  # 60KB allowance
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
            _ = client._get_connection()
            client.close()
            return client

        alive, total = self.create_memory_stress_test(create_client, 50)

        # Most clients should be garbage collected after closing (allow up to 10% due to executor cleanup timing)
        max_alive = max(2, total // 10)  # Allow up to 10% or at least 2
        assert (
            alive <= max_alive
        ), f"{alive} out of {total} clients not garbage collected"

    @patch("ffiec_data_connect.methods.collect_data")
    def test_parallel_processing_memory(self, mock_collect_data):
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

    @patch("ffiec_data_connect.methods._client_factory")
    def test_soap_client_caching_memory(self, mock_client_factory):
        """Test memory usage of SOAP client caching."""
        mock_soap_client = Mock()
        mock_soap_client.service = Mock()
        mock_soap_client.service.RetrievePanelOfReporters.return_value = Mock()
        mock_client_factory.return_value = mock_soap_client

        def create_many_cached_clients():
            creds = Mock(spec=WebserviceCredentials)
            conn = Mock(spec=FFIECConnection)

            # This should reuse cached clients
            for _ in range(100):
                methods._client_factory(conn, creds, "call")

        result, peak, growth, rss_growth = self.measure_memory_usage(
            create_many_cached_clients
        )

        # Client caching should prevent excessive memory growth
        max_expected_growth = 100 * 2000  # 200KB allowance (mock objects have overhead)
        assert (
            growth < max_expected_growth
        ), f"SOAP client caching inefficient: {growth} bytes"

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

    @patch("ffiec_data_connect.methods.collect_data")
    def test_full_workflow_memory_stability(self, mock_collect_data):
        """Test memory stability during full workflow simulation."""
        mock_collect_data.return_value = [
            {"test": "data", "size": "x" * 1000}
        ]  # 1KB per result

        def simulate_full_workflow():
            # Simulate real usage pattern
            creds = WebserviceCredentials("test_user", "test_pass")
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
                # Do some work
                _ = client._get_connection()

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

    def test_exception_handling_memory_cleanup(self):
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
            50 * 4000
        )  # 200KB allowance (exceptions have stack trace overhead)
        assert (
            growth < max_expected_growth
        ), f"Exception handling leaked memory: {growth} bytes"


class TestMemoryPressureScenarios(MemoryTestBase):
    """Test behavior under memory pressure scenarios."""

    def test_high_volume_object_creation(self):
        """Test memory behavior with high volume object creation."""

        def create_high_volume_objects():
            objects = []

            # Create many objects rapidly
            for i in range(1000):
                creds = WebserviceCredentials(f"user_{i}", f"pass_{i}")
                conn = FFIECConnection()
                client = AsyncCompatibleClient(creds)

                objects.append((creds, conn, client))

                # Periodic cleanup
                if i % 100 == 0:
                    # Clean up some old objects
                    for j in range(min(10, len(objects))):
                        _, old_conn, old_client = objects[j]
                        old_conn.close()
                        old_client.close()

            # Final cleanup
            for _, conn, client in objects:
                conn.close()
                client.close()

            return len(objects)

        result, peak, growth, rss_growth = self.measure_memory_usage(
            create_high_volume_objects
        )

        # High volume creation should manage memory reasonably
        max_expected_growth = 1000 * 10000  # 10MB allowance
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

                # Create FFIEC objects
                creds = WebserviceCredentials(f"user_{i}", f"pass_{i}")
                conn = FFIECConnection()
                client = AsyncCompatibleClient(creds)

                # Use and cleanup immediately
                _ = client._get_connection()
                conn.close()
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
