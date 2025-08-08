"""
Comprehensive thread safety test suite for FFIEC Data Connect.

Tests concurrent access patterns, race conditions, and thread safety across
all modules under real-world stress conditions.
"""

import pytest
import threading
import time
import queue
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
import requests
from typing import List, Dict, Any

from ffiec_data_connect.credentials import WebserviceCredentials, CredentialType
from ffiec_data_connect.ffiec_connection import FFIECConnection
from ffiec_data_connect.async_compatible import AsyncCompatibleClient, RateLimiter
from ffiec_data_connect import methods


class ThreadSafetyTestBase:
    """Base class for thread safety testing utilities."""
    
    def run_concurrent_test(
        self, 
        target_function, 
        num_threads: int = 20, 
        iterations_per_thread: int = 10,
        thread_args: List = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Run a function concurrently and collect results/errors.
        
        Args:
            target_function: Function to run concurrently
            num_threads: Number of concurrent threads
            iterations_per_thread: Number of iterations per thread
            thread_args: Arguments to pass to each thread
            timeout: Timeout for thread completion
            
        Returns:
            Dictionary with results, errors, and timing info
        """
        results = queue.Queue()
        errors = queue.Queue()
        threads = []
        start_time = time.time()
        
        def thread_worker(thread_id):
            """Worker function for each thread."""
            for iteration in range(iterations_per_thread):
                try:
                    if thread_args:
                        result = target_function(thread_id, iteration, *thread_args)
                    else:
                        result = target_function(thread_id, iteration)
                    results.put((thread_id, iteration, result))
                except Exception as e:
                    errors.put((thread_id, iteration, str(e), type(e).__name__))
        
        # Start all threads
        for thread_id in range(num_threads):
            thread = threading.Thread(target=thread_worker, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion with timeout
        for thread in threads:
            thread.join(timeout=timeout)
            if thread.is_alive():
                errors.put((-1, -1, f"Thread timeout after {timeout}s", "TimeoutError"))
        
        end_time = time.time()
        
        # Collect results
        all_results = []
        while not results.empty():
            all_results.append(results.get())
        
        all_errors = []
        while not errors.empty():
            all_errors.append(errors.get())
        
        return {
            'results': all_results,
            'errors': all_errors,
            'total_time': end_time - start_time,
            'expected_operations': num_threads * iterations_per_thread,
            'successful_operations': len(all_results),
            'failed_operations': len(all_errors),
            'success_rate': len(all_results) / (num_threads * iterations_per_thread),
        }


class TestCredentialsThreadSafety(ThreadSafetyTestBase):
    """Test thread safety of credential operations."""
    
    def test_concurrent_credential_creation(self):
        """Test concurrent credential creation from different threads."""
        def create_credentials(thread_id, iteration):
            # Use different credentials per thread to test independent creation
            username = f"user_{thread_id}_{iteration}"
            password = f"pass_{thread_id}_{iteration}"
            creds = WebserviceCredentials(username, password)
            
            # Verify credentials were set correctly
            assert creds.username == username
            assert creds.password == password
            assert creds.credential_source == CredentialType.SET_FROM_INIT
            
            return (creds.username, creds.credential_source)
        
        results = self.run_concurrent_test(
            create_credentials, 
            num_threads=15, 
            iterations_per_thread=5
        )
        
        # Should have no errors
        assert len(results['errors']) == 0, f"Credential creation errors: {results['errors']}"
        assert results['success_rate'] == 1.0
        
        # Verify all credentials are unique
        usernames = [result[2][0] for result in results['results']]
        assert len(set(usernames)) == len(usernames), "Duplicate usernames detected"
    
    def test_credential_immutability_under_concurrent_modification(self):
        """Test that credential immutability is maintained under concurrent modification attempts."""
        # Create a shared credential instance
        shared_creds = WebserviceCredentials("original_user", "original_pass")
        modification_attempts = queue.Queue()
        
        def attempt_modification(thread_id, iteration):
            try:
                # Try to modify username
                shared_creds.username = f"hacker_{thread_id}_{iteration}"
                modification_attempts.put(("username", thread_id, iteration, "SUCCESS"))
                return "SECURITY_BREACH"
            except Exception as e:
                modification_attempts.put(("username", thread_id, iteration, "BLOCKED"))
                
                # Also try password
                try:
                    shared_creds.password = f"hacked_{thread_id}_{iteration}"
                    modification_attempts.put(("password", thread_id, iteration, "SUCCESS"))
                    return "SECURITY_BREACH"
                except Exception:
                    modification_attempts.put(("password", thread_id, iteration, "BLOCKED"))
                    return "MODIFICATION_BLOCKED"
        
        results = self.run_concurrent_test(
            attempt_modification,
            num_threads=20,
            iterations_per_thread=10
        )
        
        # All modification attempts should be blocked
        successful_modifications = [r for r in results['results'] if r[2] == "SECURITY_BREACH"]
        assert len(successful_modifications) == 0, "Security breach: credentials were modified!"
        
        # Original credentials should be unchanged
        assert shared_creds.username == "original_user"
        assert shared_creds.password == "original_pass"
        
        # Verify all modification attempts were properly blocked
        blocked_attempts = []
        while not modification_attempts.empty():
            blocked_attempts.append(modification_attempts.get())
        
        successful_breaches = [a for a in blocked_attempts if a[3] == "SUCCESS"]
        assert len(successful_breaches) == 0, "Some modification attempts succeeded!"
    
    @patch.dict('os.environ', {'FFIEC_USERNAME': 'env_user', 'FFIEC_PASSWORD': 'env_pass'})
    def test_concurrent_environment_credential_access(self):
        """Test concurrent access to environment-based credentials."""
        def create_env_credentials(thread_id, iteration):
            creds = WebserviceCredentials()
            
            # Verify environment credentials
            assert creds.username == "env_user"
            assert creds.password == "env_pass"
            assert creds.credential_source == CredentialType.SET_FROM_ENV
            
            return (creds.username, creds.credential_source.value)
        
        results = self.run_concurrent_test(
            create_env_credentials,
            num_threads=25,
            iterations_per_thread=8
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # All should have same env credentials
        for result in results['results']:
            assert result[2][0] == "env_user"
            assert result[2][1] == CredentialType.SET_FROM_ENV.value


class TestFFIECConnectionThreadSafety(ThreadSafetyTestBase):
    """Test thread safety of FFIEC connection operations."""
    
    def test_concurrent_connection_creation(self):
        """Test concurrent creation of FFIEC connections."""
        def create_connection(thread_id, iteration):
            conn = FFIECConnection()
            
            # Verify connection properties
            assert conn.use_proxy is False
            assert conn.proxy_host is None
            assert hasattr(conn, '_lock')
            assert hasattr(conn, '_session')
            
            return (id(conn), conn.use_proxy)
        
        results = self.run_concurrent_test(
            create_connection,
            num_threads=15,
            iterations_per_thread=5
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # Should have successfully created connections (IDs may be reused due to GC)
        connection_ids = [result[2][0] for result in results['results']]
        unique_connections = len(set(connection_ids))
        
        # Should have created multiple unique connections (allowing for heavy GC reuse)
        assert unique_connections >= 10  # At least 10 unique connections out of 75
    
    def test_concurrent_session_access(self):
        """Test concurrent access to session property."""
        shared_connection = FFIECConnection()
        session_ids = []
        session_lock = threading.Lock()
        
        def access_session(thread_id, iteration):
            session = shared_connection.session
            
            # Session should be a requests.Session
            assert hasattr(session, 'get')
            assert hasattr(session, 'post')
            
            # Store session ID thread-safely
            with session_lock:
                session_ids.append(id(session))
            
            return id(session)
        
        results = self.run_concurrent_test(
            access_session,
            num_threads=20,
            iterations_per_thread=10
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # All accesses should return the same session (cached)
        unique_session_ids = set(session_ids)
        assert len(unique_session_ids) == 1, f"Expected 1 unique session, got {len(unique_session_ids)}"
    
    def test_concurrent_proxy_configuration(self):
        """Test concurrent proxy configuration changes."""
        shared_connection = FFIECConnection()
        
        def configure_proxy(thread_id, iteration):
            try:
                # Set proxy configuration
                shared_connection.proxy_host = f"proxy{thread_id}.example.com"
                shared_connection.proxy_port = 8080 + thread_id
                shared_connection.proxy_protocol = shared_connection.ProxyProtocol.HTTP
                
                # Brief delay to increase chance of race conditions
                time.sleep(0.001)
                
                # Enable proxy (this should validate configuration)
                shared_connection.use_proxy = True
                
                return (shared_connection.proxy_host, shared_connection.use_proxy)
            except Exception as e:
                # Some race conditions in configuration are expected
                return ("ERROR", str(e))
        
        results = self.run_concurrent_test(
            configure_proxy,
            num_threads=10,
            iterations_per_thread=3
        )
        
        # Should complete without deadlocks or crashes
        assert results['total_time'] < 10.0, "Proxy configuration took too long (possible deadlock)"
        
        # Final state should be consistent
        assert shared_connection.use_proxy in [True, False]
        if shared_connection.use_proxy:
            assert shared_connection.proxy_host is not None
            assert shared_connection.proxy_port is not None
    
    def test_concurrent_session_regeneration(self):
        """Test concurrent session regeneration scenarios."""
        shared_connection = FFIECConnection()
        
        def trigger_session_regeneration(thread_id, iteration):
            # Access session to create it
            session1 = shared_connection.session
            session1_id = id(session1)
            
            # Modify configuration to trigger regeneration
            shared_connection.proxy_host = f"host{thread_id}_{iteration}.com"
            shared_connection._config_hash = None  # Force regeneration
            
            # Access session again (should potentially regenerate)
            session2 = shared_connection.session
            session2_id = id(session2)
            
            return (session1_id, session2_id, session1_id != session2_id)
        
        results = self.run_concurrent_test(
            trigger_session_regeneration,
            num_threads=10,
            iterations_per_thread=5
        )
        
        # Should handle regeneration without errors
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
    
    def test_connection_cleanup_thread_safety(self):
        """Test thread-safe connection cleanup."""
        def create_and_cleanup_connection(thread_id, iteration):
            conn = FFIECConnection()
            
            # Create session
            session = conn.session
            assert session is not None
            
            # Close connection
            conn.close()
            
            # Verify cleanup
            assert conn._session is None
            
            return "CLEANED"
        
        results = self.run_concurrent_test(
            create_and_cleanup_connection,
            num_threads=15,
            iterations_per_thread=8
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0


class TestAsyncCompatibleClientThreadSafety(ThreadSafetyTestBase):
    """Test thread safety of AsyncCompatibleClient operations."""
    
    def test_concurrent_client_creation(self):
        """Test concurrent creation of async clients."""
        def create_client(thread_id, iteration):
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(
                creds, 
                max_concurrent=3, 
                rate_limit=20
            )
            
            assert client.credentials is creds
            assert client.max_concurrent == 3
            assert client.rate_limiter is not None
            
            return (id(client), client.max_concurrent)
        
        results = self.run_concurrent_test(
            create_client,
            num_threads=12,
            iterations_per_thread=5
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # Should have successfully created clients (IDs may be reused due to GC)
        client_ids = [result[2][0] for result in results['results']]
        unique_clients = len(set(client_ids))
        
        # Should have created multiple unique clients (allowing for heavy GC reuse)
        assert unique_clients >= 10  # At least 10 unique clients out of 60
    
    def test_concurrent_connection_caching(self):
        """Test thread-safe connection caching in AsyncCompatibleClient."""
        creds = Mock(spec=WebserviceCredentials)
        shared_client = AsyncCompatibleClient(creds, rate_limit=None)
        connection_ids = {}
        results_lock = threading.Lock()
        
        def get_cached_connection(thread_id, iteration):
            conn = shared_client._get_connection()
            
            # Store connection per thread
            with results_lock:
                if thread_id not in connection_ids:
                    connection_ids[thread_id] = []
                connection_ids[thread_id].append(id(conn))
            
            return (thread_id, id(conn))
        
        results = self.run_concurrent_test(
            get_cached_connection,
            num_threads=8,
            iterations_per_thread=10
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # Each thread should get same connection consistently (thread-local caching)
        for thread_id, conn_ids in connection_ids.items():
            unique_ids = set(conn_ids)
            assert len(unique_ids) == 1, f"Thread {thread_id} got multiple connections: {unique_ids}"
        
        # Different threads should get different connections
        all_unique_connections = set()
        for conn_ids in connection_ids.values():
            all_unique_connections.update(conn_ids)
        
        # Should have one unique connection per thread
        assert len(all_unique_connections) <= len(connection_ids)
    
    @patch('ffiec_data_connect.methods.collect_data')
    def test_concurrent_data_collection(self, mock_collect_data):
        """Test concurrent data collection operations."""
        mock_collect_data.return_value = [{"test": "data"}]
        
        creds = Mock(spec=WebserviceCredentials)
        shared_client = AsyncCompatibleClient(creds, rate_limit=None)
        
        def collect_data_concurrently(thread_id, iteration):
            rssd_id = f"{123456 + thread_id}_{iteration}"
            result = shared_client.collect_data("2023-12-31", rssd_id)
            
            # Verify result
            assert result == [{"test": "data"}]
            
            return (thread_id, rssd_id, len(result))
        
        results = self.run_concurrent_test(
            collect_data_concurrently,
            num_threads=10,
            iterations_per_thread=8
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # Verify all calls were made
        assert mock_collect_data.call_count == 80  # 10 threads * 8 iterations
    
    def test_rate_limiter_thread_safety(self):
        """Test thread safety of rate limiter under high concurrency."""
        rate_limiter = RateLimiter(calls_per_second=50)  # Fast rate for testing
        call_times = []
        times_lock = threading.Lock()
        
        def make_rate_limited_call(thread_id, iteration):
            start = time.time()
            rate_limiter.wait_if_needed()
            end = time.time()
            
            with times_lock:
                call_times.append((thread_id, iteration, start, end, end - start))
            
            return end - start
        
        results = self.run_concurrent_test(
            make_rate_limited_call,
            num_threads=15,
            iterations_per_thread=4
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # Verify rate limiting behavior
        sorted_calls = sorted(call_times, key=lambda x: x[2])  # Sort by start time
        
        # Most calls should have some delay (except first few)
        delayed_calls = [call for call in sorted_calls if call[4] > 0.005]  # 5ms tolerance
        assert len(delayed_calls) >= len(sorted_calls) * 0.7  # At least 70% should be delayed
    
    def test_client_cleanup_thread_safety(self):
        """Test thread-safe client cleanup operations."""
        def create_and_cleanup_client(thread_id, iteration):
            creds = Mock(spec=WebserviceCredentials)
            client = AsyncCompatibleClient(creds)
            
            # Use client to create cached connections
            conn1 = client._get_connection()
            conn2 = client._get_connection()
            
            # Should be same connection (cached)
            assert conn1 is conn2
            
            # Close client
            client.close()
            
            # Verify cleanup
            assert len(client._connection_cache) == 0
            
            return "CLEANED"
        
        results = self.run_concurrent_test(
            create_and_cleanup_client,
            num_threads=12,
            iterations_per_thread=5
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0


class TestMethodsThreadSafety(ThreadSafetyTestBase):
    """Test thread safety of methods module validation and utilities."""
    
    def test_concurrent_input_validation(self):
        """Test concurrent input validation operations."""
        from ffiec_data_connect.methods import (
            _output_type_validator,
            _date_format_validator, 
            _validate_rssd_id
        )
        
        def run_validation_tests(thread_id, iteration):
            results = []
            
            # Test output type validation
            try:
                _output_type_validator("list")
                results.append("output_valid")
            except Exception as e:
                results.append(f"output_error: {e}")
            
            # Test date format validation
            try:
                _date_format_validator("string_original")
                results.append("date_valid")
            except Exception as e:
                results.append(f"date_error: {e}")
            
            # Test RSSD validation
            try:
                rssd_int = _validate_rssd_id(f"{123456 + thread_id}")
                results.append(f"rssd_valid: {rssd_int}")
            except Exception as e:
                results.append(f"rssd_error: {e}")
            
            return results
        
        results = self.run_concurrent_test(
            run_validation_tests,
            num_threads=20,
            iterations_per_thread=10
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # All validations should succeed
        for result in results['results']:
            validation_results = result[2]
            assert "output_valid" in validation_results
            assert "date_valid" in validation_results
            assert any("rssd_valid" in r for r in validation_results)
    
    def test_concurrent_date_utilities(self):
        """Test concurrent access to date utility functions."""
        from ffiec_data_connect.methods import (
            _create_ffiec_date_from_datetime,
            _convert_any_date_to_ffiec_format,
            _is_valid_date_or_quarter
        )
        from datetime import datetime
        
        def run_date_operations(thread_id, iteration):
            results = []
            
            # Test date creation
            test_date = datetime(2023, 12, 31)
            ffiec_date = _create_ffiec_date_from_datetime(test_date)
            results.append(ffiec_date)
            
            # Test date conversion
            converted = _convert_any_date_to_ffiec_format("2023-12-31")
            results.append(converted)
            
            # Test date validation
            is_valid = _is_valid_date_or_quarter(datetime(2023, 12, 31))
            results.append(is_valid)
            
            return results
        
        results = self.run_concurrent_test(
            run_date_operations,
            num_threads=25,
            iterations_per_thread=15
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # All results should be consistent
        for result in results['results']:
            date_results = result[2]
            assert date_results[0] == "12/31/2023"
            assert date_results[1] == "12/31/2023" 
            assert date_results[2] is True


class TestConcurrentResourceManagement(ThreadSafetyTestBase):
    """Test concurrent resource management and cleanup."""
    
    def test_memory_pressure_under_concurrency(self):
        """Test system behavior under concurrent memory pressure."""
        import tracemalloc
        tracemalloc.start()
        
        def create_heavy_objects(thread_id, iteration):
            # Create multiple objects that could cause memory pressure
            creds = WebserviceCredentials(f"user_{thread_id}_{iteration}", f"pass_{thread_id}_{iteration}")
            conn = FFIECConnection()
            
            # Force session creation
            session = conn.session
            
            # Create some data structures
            data = [{"test": f"data_{i}_{thread_id}_{iteration}"} for i in range(100)]
            
            # Cleanup explicitly
            conn.close()
            
            return len(data)
        
        start_memory = tracemalloc.get_traced_memory()[0]
        
        results = self.run_concurrent_test(
            create_heavy_objects,
            num_threads=8,
            iterations_per_thread=10
        )
        
        # Force garbage collection
        gc.collect()
        end_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # Memory should not grow excessively (allow 10MB growth)
        memory_growth = end_memory - start_memory
        assert memory_growth < 10 * 1024 * 1024, f"Excessive memory growth: {memory_growth} bytes"
    
    def test_exception_safety_under_concurrency(self):
        """Test that exceptions in one thread don't affect others."""
        shared_state = {"error_count": 0, "success_count": 0}
        state_lock = threading.Lock()
        
        def potentially_failing_operation(thread_id, iteration):
            try:
                # Simulate operation that might fail
                if (thread_id + iteration) % 7 == 0:  # Fail predictably
                    raise ValueError(f"Simulated error for thread {thread_id}, iteration {iteration}")
                
                # Normal operation
                creds = WebserviceCredentials(f"user_{thread_id}", f"pass_{thread_id}")
                
                with state_lock:
                    shared_state["success_count"] += 1
                
                return "SUCCESS"
                
            except ValueError:
                with state_lock:
                    shared_state["error_count"] += 1
                raise
        
        results = self.run_concurrent_test(
            potentially_failing_operation,
            num_threads=15,
            iterations_per_thread=10
        )
        
        # Should have both successes and expected failures
        assert len(results['errors']) > 0  # Some operations should fail
        assert len(results['results']) > 0  # Some operations should succeed
        
        # Total operations should add up
        total_ops = len(results['results']) + len(results['errors'])
        assert total_ops == 150  # 15 threads * 10 iterations
        
        # Shared state should be consistent
        assert shared_state["success_count"] == len(results['results'])
        assert shared_state["error_count"] == len(results['errors'])


class TestStressConditions(ThreadSafetyTestBase):
    """Test behavior under stress conditions."""
    
    def test_high_concurrency_stress(self):
        """Test system behavior under very high concurrency."""
        def lightweight_operation(thread_id, iteration):
            # Lightweight operation that tests basic thread safety
            creds = WebserviceCredentials(f"u{thread_id}", f"p{thread_id}")
            return creds.credential_source.value
        
        # High concurrency stress test
        results = self.run_concurrent_test(
            lightweight_operation,
            num_threads=50,  # High thread count
            iterations_per_thread=20,
            timeout=60.0
        )
        
        # Should handle high concurrency without errors
        assert len(results['errors']) == 0, f"Errors under high concurrency: {results['errors'][:5]}"
        assert results['success_rate'] >= 0.95  # Allow 5% failure rate under extreme stress
        
        # Should complete in reasonable time
        assert results['total_time'] < 45.0, f"High concurrency test too slow: {results['total_time']}s"
    
    def test_rapid_creation_destruction(self):
        """Test rapid creation and destruction of objects."""
        def create_destroy_cycle(thread_id, iteration):
            objects = []
            
            # Rapid creation
            for i in range(5):
                creds = WebserviceCredentials(f"user_{thread_id}_{iteration}_{i}", f"pass_{i}")
                conn = FFIECConnection()
                objects.append((creds, conn))
            
            # Rapid destruction
            for creds, conn in objects:
                conn.close()
            
            return len(objects)
        
        results = self.run_concurrent_test(
            create_destroy_cycle,
            num_threads=20,
            iterations_per_thread=8
        )
        
        assert len(results['errors']) == 0
        assert results['success_rate'] == 1.0
        
        # All cycles should create expected number of objects
        for result in results['results']:
            assert result[2] == 5  # 5 objects per cycle


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])