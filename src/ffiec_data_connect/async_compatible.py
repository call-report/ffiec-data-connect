"""
Async-compatible client for FFIEC Data Connect.

This module provides async/await support and parallel processing capabilities
while maintaining backward compatibility with the synchronous API.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ffiec_data_connect import credentials, ffiec_connection, methods
from ffiec_data_connect.credentials import OAuth2Credentials


class RateLimiter:
    """Thread-safe rate limiter for both sync and async use."""

    def __init__(self, calls_per_second: float = 10) -> None:
        """Initialize rate limiter.

        Args:
            calls_per_second: Maximum number of calls per second allowed
        """
        self.calls_per_second: float = calls_per_second
        self.min_interval: float = 1.0 / calls_per_second
        self.last_call: float = 0.0
        self.lock = threading.Lock()

    def wait_if_needed(self) -> None:
        """Synchronous rate limit wait."""
        with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call = time.time()

    async def async_wait_if_needed(self) -> None:
        """Asynchronous rate limit wait."""
        # For async contexts, we need to be careful about blocking
        # Use a simple approach to avoid threading issues in async
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


class AsyncCompatibleClient:
    """Client that supports both sync and async usage patterns.

    This client provides:
    - Backward compatible synchronous methods
    - Parallel processing with thread pools
    - Async/await support for integration with async frameworks
    - Rate limiting to respect API limits
    - Thread-safe operation
    """

    def __init__(
        self,
        credentials: Union[credentials.WebserviceCredentials, "OAuth2Credentials"],
        max_concurrent: int = 5,
        rate_limit: Optional[float] = 10,  # requests per second
        executor: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        """Initialize the async-compatible client.

        **ENHANCED**: Now supports both SOAP and REST APIs automatically based on credential type.
        For better performance, use OAuth2Credentials for REST API access.

        Args:
            credentials: Either WebserviceCredentials (SOAP) or OAuth2Credentials (REST)
            max_concurrent: Maximum concurrent requests
            rate_limit: Maximum requests per second (None to disable)
            executor: Optional thread pool executor to use
        """
        self.credentials = credentials
        self.max_concurrent = max_concurrent
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit else None
        self.executor = executor or ThreadPoolExecutor(max_workers=max_concurrent)

        # Enhanced for dual protocol support
        from .credentials import OAuth2Credentials

        self._is_rest_client = isinstance(credentials, OAuth2Credentials)

        if self._is_rest_client:
            # REST clients don't need connection caching
            self._connection_cache: Dict[int, ffiec_connection.FFIECConnection] = {}
        else:
            # SOAP clients use connection caching
            self._connection_cache = {}

        self._lock = threading.Lock()
        self._owned_executor = executor is None  # Track if we created the executor

    # ===== Synchronous Methods (Backward Compatible) =====

    def collect_data(
        self,
        reporting_period: str,
        rssd_id: str,
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
    ) -> Union[List[Dict[str, Any]], Any]:
        """Standard synchronous method - backward compatible.

        Args:
            reporting_period: Reporting period (e.g., "2020-03-31" or "1Q2020")
            rssd_id: RSSD ID of the institution
            series: Data series ("call" or "ubpr")
            output_type: Output format ("list", "pandas", or "polars")
            date_output_format: Date format in output

        Returns:
            Collected data in requested format
        """
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        # Enhanced for dual protocol support
        if self._is_rest_client:
            # REST API doesn't need a connection object
            return methods.collect_data(
                None,
                self.credentials,
                reporting_period,
                rssd_id,
                series,
                output_type,
                date_output_format,
            )
        else:
            # SOAP API uses cached connection
            conn = self._get_connection()
            return methods.collect_data(
                conn,
                self.credentials,
                reporting_period,
                rssd_id,
                series,
                output_type,
                date_output_format,
            )

    def collect_reporting_periods(
        self,
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
    ) -> Union[List[str], Any]:
        """Get available reporting periods - backward compatible.

        Args:
            series: Data series ("call" or "ubpr")
            output_type: Output format ("list", "pandas", or "polars")
            date_output_format: Date format in output

        Returns:
            Available reporting periods in ascending chronological order (oldest first)
        """
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        # Enhanced for dual protocol support
        if self._is_rest_client:
            # REST API doesn't need a connection object
            return methods.collect_reporting_periods(
                None, self.credentials, series, output_type, date_output_format
            )
        else:
            # SOAP API uses cached connection
            conn = self._get_connection()
            return methods.collect_reporting_periods(
                conn, self.credentials, series, output_type, date_output_format
            )

    def collect_data_parallel(
        self,
        reporting_period: str,
        rssd_ids: List[str],
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """Collect data for multiple banks in parallel (sync interface).

        Args:
            reporting_period: Reporting period
            rssd_ids: List of RSSD IDs
            series: Data series
            output_type: Output format
            date_output_format: Date format
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping RSSD IDs to their data or error info
        """
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {}

            for rssd_id in rssd_ids:
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()

                future = executor.submit(
                    self.collect_data,
                    reporting_period,
                    rssd_id,
                    series,
                    output_type,
                    date_output_format,
                )
                futures[future] = rssd_id

            results = {}
            for future in as_completed(futures):
                rssd_id = futures[future]
                try:
                    result = future.result()
                    results[rssd_id] = result
                    if progress_callback:
                        progress_callback(rssd_id, result)
                except Exception as e:
                    results[rssd_id] = {"error": str(e), "rssd_id": rssd_id}
                    if progress_callback:
                        progress_callback(rssd_id, {"error": str(e)})

            return results

    def collect_time_series(
        self,
        rssd_id: str,
        reporting_periods: List[str],
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
    ) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """Collect multiple periods for one bank in parallel (sync interface).

        Args:
            rssd_id: RSSD ID of the institution
            reporting_periods: List of reporting periods
            series: Data series
            output_type: Output format
            date_output_format: Date format

        Returns:
            Dictionary mapping periods to their data
        """
        with ThreadPoolExecutor(
            max_workers=min(len(reporting_periods), self.max_concurrent)
        ) as executor:
            futures = {}

            for period in reporting_periods:
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()

                future = executor.submit(
                    self.collect_data,
                    period,
                    rssd_id,
                    series,
                    output_type,
                    date_output_format,
                )
                futures[future] = period

            results = {}
            for future in as_completed(futures):
                period = futures[future]
                try:
                    results[period] = future.result()
                except Exception as e:
                    results[period] = {"error": str(e), "period": period}

            return results

    # ===== Async Methods (New Functionality) =====

    async def collect_data_async(
        self,
        reporting_period: str,
        rssd_id: str,
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
    ) -> Union[List[Dict[str, Any]], Any]:
        """Async version - runs sync code in thread pool.

        Args:
            reporting_period: Reporting period
            rssd_id: RSSD ID of the institution
            series: Data series
            output_type: Output format
            date_output_format: Date format

        Returns:
            Collected data in requested format
        """
        if self.rate_limiter:
            await self.rate_limiter.async_wait_if_needed()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.collect_data,
            reporting_period,
            rssd_id,
            series,
            output_type,
            date_output_format,
        )

    async def collect_batch_async(
        self,
        reporting_period: str,
        rssd_ids: List[str],
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """Collect data for multiple banks with rate limiting and progress tracking.

        Args:
            reporting_period: Reporting period
            rssd_ids: List of RSSD IDs
            series: Data series
            output_type: Output format
            date_output_format: Date format
            progress_callback: Optional async callback for progress

        Returns:
            Dictionary mapping RSSD IDs to their data
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = {}

        async def fetch_one(rssd_id: str) -> Tuple[str, Any]:
            async with semaphore:
                try:
                    if self.rate_limiter:
                        await self.rate_limiter.async_wait_if_needed()

                    result = await self.collect_data_async(
                        reporting_period,
                        rssd_id,
                        series,
                        output_type,
                        date_output_format,
                    )

                    if progress_callback:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(rssd_id, result)  # type: ignore[attr-defined]
                        else:
                            progress_callback(rssd_id, result)

                    return rssd_id, result
                except Exception as e:
                    error_result = {"error": str(e), "rssd_id": rssd_id}
                    if progress_callback:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(rssd_id, error_result)  # type: ignore[attr-defined]
                        else:
                            progress_callback(rssd_id, error_result)
                    return rssd_id, error_result

        tasks = [fetch_one(rssd_id) for rssd_id in rssd_ids]

        for coro in asyncio.as_completed(tasks):
            rssd_id, result = await coro
            results[rssd_id] = result

        return results

    async def collect_time_series_async(
        self,
        rssd_id: str,
        reporting_periods: List[str],
        series: str = "call",
        output_type: str = "list",
        date_output_format: str = "string_original",
    ) -> Dict[str, Union[List[Dict[str, Any]], Dict[str, Any]]]:
        """Collect multiple periods for one bank in parallel (async).

        Args:
            rssd_id: RSSD ID of the institution
            reporting_periods: List of reporting periods
            series: Data series
            output_type: Output format
            date_output_format: Date format

        Returns:
            Dictionary mapping periods to their data
        """
        tasks = []
        for period in reporting_periods:
            task = self.collect_data_async(
                period, rssd_id, series, output_type, date_output_format
            )
            tasks.append((period, task))

        results = {}
        for period, task in tasks:
            try:
                results[period] = await task
            except Exception as e:
                results[period] = {"error": str(e), "period": period}

        return results

    # ===== Helper Methods =====

    def _get_connection(self) -> ffiec_connection.FFIECConnection:
        """Get or create thread-local connection.

        Returns:
            Thread-local FFIECConnection instance
        """
        thread_id = threading.get_ident()
        with self._lock:
            if thread_id not in self._connection_cache:
                self._connection_cache[thread_id] = ffiec_connection.FFIECConnection()
            return self._connection_cache[thread_id]

    def close(self) -> None:
        """Close all connections and cleanup resources."""
        with self._lock:
            # Close all cached connections
            for conn in self._connection_cache.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._connection_cache.clear()

            # Shutdown executor if we created it
            if self._owned_executor and self.executor:
                self.executor.shutdown(wait=True)

    # ===== Context Manager Support =====

    def __enter__(self) -> "AsyncCompatibleClient":
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sync context manager exit - cleanup."""
        self.close()

    async def __aenter__(self) -> "AsyncCompatibleClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - cleanup."""
        self.close()
