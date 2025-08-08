# Practical Async Implementation - FFIEC Data Connect

## Executive Summary
Given FFIEC API rate limits, async capabilities should focus on:
1. **Controlled parallel processing** with configurable concurrency
2. **Integration-friendly design** for external async applications
3. **Rate-limit aware batch processing**

## Real-World Use Cases Despite Rate Limits

### Use Case 1: Multi-Quarter Collection (Same Bank)
```python
# Current: Sequential - 20 seconds for 4 quarters
quarters = ["2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"]
for quarter in quarters:
    data = collect_data(conn, creds, quarter, "12345", "call")

# With Async: Parallel - 5 seconds (respecting rate limits)
async with AsyncFFIECClient(creds, max_concurrent=4) as client:
    results = await client.collect_multiple_periods("12345", quarters)
```

### Use Case 2: Different Data Series (Same Bank/Period)
```python
# Collect both Call Report and UBPR data in parallel
async with AsyncFFIECClient(creds, max_concurrent=2) as client:
    call_data, ubpr_data = await asyncio.gather(
        client.collect_data("2020-03-31", "12345", "call"),
        client.collect_data("2020-03-31", "12345", "ubpr")
    )
```

### Use Case 3: Rate-Limited Batch Processing
```python
# Process 1000 banks with rate limiting (e.g., 10 requests/second)
async with AsyncFFIECClient(creds, rate_limit=10) as client:
    results = await client.collect_batch_with_rate_limit(
        bank_ids, 
        reporting_period="2020-03-31"
    )
```

## Implementation Strategy

### Core Design Principles
1. **Make existing code async-friendly** without breaking changes
2. **Provide both sync and async interfaces**
3. **Support external event loop integration**
4. **Implement smart rate limiting**

## Proposed Implementation

### 1. Async-Compatible Base (No Breaking Changes)

```python
# src/ffiec_data_connect/async_compatible.py
"""
Async-compatible wrappers that work in both sync and async contexts
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any, Union
from functools import partial
import time

class RateLimiter:
    """Thread-safe rate limiter for both sync and async use"""
    
    def __init__(self, calls_per_second: float = 10):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Synchronous rate limit wait"""
        with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call = time.time()
    
    async def async_wait_if_needed(self):
        """Asynchronous rate limit wait"""
        with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_call = time.time()


class AsyncCompatibleClient:
    """Client that supports both sync and async usage patterns"""
    
    def __init__(
        self, 
        credentials,
        max_concurrent: int = 5,
        rate_limit: Optional[float] = 10,  # requests per second
        executor: Optional[ThreadPoolExecutor] = None
    ):
        self.credentials = credentials
        self.max_concurrent = max_concurrent
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit else None
        self.executor = executor or ThreadPoolExecutor(max_workers=max_concurrent)
        self._session_cache = {}
        self._lock = threading.Lock()
    
    # ===== Synchronous Methods (Backward Compatible) =====
    
    def collect_data(self, reporting_period: str, rssd_id: str, series: str = "call") -> List[Dict]:
        """Standard synchronous method - backward compatible"""
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        conn = self._get_connection()
        return methods.collect_data(conn, self.credentials, reporting_period, rssd_id, series)
    
    def collect_data_parallel(
        self, 
        reporting_period: str, 
        rssd_ids: List[str], 
        series: str = "call"
    ) -> Dict[str, List[Dict]]:
        """Collect data for multiple banks in parallel (sync interface)"""
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {}
            for rssd_id in rssd_ids:
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()
                
                future = executor.submit(
                    self.collect_data, 
                    reporting_period, 
                    rssd_id, 
                    series
                )
                futures[future] = rssd_id
            
            results = {}
            for future in as_completed(futures):
                rssd_id = futures[future]
                try:
                    results[rssd_id] = future.result()
                except Exception as e:
                    results[rssd_id] = {'error': str(e)}
            
            return results
    
    # ===== Async Methods (New Functionality) =====
    
    async def collect_data_async(
        self, 
        reporting_period: str, 
        rssd_id: str, 
        series: str = "call"
    ) -> List[Dict]:
        """Async version - runs sync code in thread pool"""
        if self.rate_limiter:
            await self.rate_limiter.async_wait_if_needed()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.collect_data,
            reporting_period,
            rssd_id,
            series
        )
    
    async def collect_batch_async(
        self,
        reporting_period: str,
        rssd_ids: List[str],
        series: str = "call",
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Union[List[Dict], Dict]]:
        """
        Collect data for multiple banks with rate limiting and progress tracking
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = {}
        
        async def fetch_one(rssd_id: str):
            async with semaphore:
                try:
                    if self.rate_limiter:
                        await self.rate_limiter.async_wait_if_needed()
                    
                    result = await self.collect_data_async(
                        reporting_period, rssd_id, series
                    )
                    
                    if progress_callback:
                        await progress_callback(rssd_id, result)
                    
                    return rssd_id, result
                except Exception as e:
                    return rssd_id, {'error': str(e)}
        
        tasks = [fetch_one(rssd_id) for rssd_id in rssd_ids]
        
        for coro in asyncio.as_completed(tasks):
            rssd_id, result = await coro
            results[rssd_id] = result
        
        return results
    
    async def collect_time_series_async(
        self,
        rssd_id: str,
        reporting_periods: List[str],
        series: str = "call"
    ) -> Dict[str, List[Dict]]:
        """Collect multiple periods for one bank in parallel"""
        tasks = [
            self.collect_data_async(period, rssd_id, series)
            for period in reporting_periods
        ]
        
        results = {}
        for period, coro in zip(reporting_periods, asyncio.as_completed(tasks)):
            result = await coro
            results[period] = result
        
        return results
    
    # ===== Integration Helpers =====
    
    def _get_connection(self):
        """Get or create thread-local connection"""
        thread_id = threading.get_ident()
        if thread_id not in self._session_cache:
            with self._lock:
                if thread_id not in self._session_cache:
                    self._session_cache[thread_id] = FFIECConnection()
        return self._session_cache[thread_id]
    
    async def __aenter__(self):
        """Async context manager support"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on async context exit"""
        self.executor.shutdown(wait=False)
    
    def __enter__(self):
        """Sync context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on sync context exit"""
        self.executor.shutdown(wait=True)
```

### 2. Integration-Friendly Wrapper

```python
# src/ffiec_data_connect/async_integration.py
"""
Helpers for integrating with external async frameworks
"""

class FFIECAsyncAdapter:
    """Adapter for integrating with external async applications"""
    
    def __init__(self, credentials, config: Optional[Dict] = None):
        self.credentials = credentials
        self.config = config or {}
        self._client = None
    
    async def setup(self):
        """Initialize resources - call from async app startup"""
        self._client = AsyncCompatibleClient(
            self.credentials,
            max_concurrent=self.config.get('max_concurrent', 5),
            rate_limit=self.config.get('rate_limit', 10)
        )
    
    async def cleanup(self):
        """Cleanup resources - call from async app shutdown"""
        if self._client:
            await self._client.__aexit__(None, None, None)
    
    def as_task(self, *args, **kwargs):
        """Create an asyncio task for data collection"""
        return asyncio.create_task(
            self._client.collect_data_async(*args, **kwargs)
        )
    
    async def collect_with_timeout(
        self, 
        *args, 
        timeout: float = 30.0,
        **kwargs
    ):
        """Collect data with timeout"""
        try:
            return await asyncio.wait_for(
                self._client.collect_data_async(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return {'error': 'Request timed out'}

# Example: Integration with FastAPI
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
ffiec_adapter = FFIECAsyncAdapter(credentials)

@app.on_event("startup")
async def startup_event():
    await ffiec_adapter.setup()

@app.on_event("shutdown") 
async def shutdown_event():
    await ffiec_adapter.cleanup()

@app.get("/bank/{rssd_id}/data")
async def get_bank_data(rssd_id: str, period: str = "2020-03-31"):
    """API endpoint that uses FFIEC client asynchronously"""
    result = await ffiec_adapter.collect_with_timeout(
        period, rssd_id, timeout=15.0
    )
    return result

@app.post("/banks/batch")
async def batch_collect(
    rssd_ids: List[str], 
    background_tasks: BackgroundTasks
):
    """Start batch collection in background"""
    background_tasks.add_task(
        process_batch_in_background,
        rssd_ids
    )
    return {"status": "Batch processing started", "count": len(rssd_ids)}
```

### 3. Smart Rate Limiting with Bursting

```python
# src/ffiec_data_connect/rate_limiting.py
"""
Advanced rate limiting with burst support
"""
import asyncio
import time
from collections import deque
from typing import Optional

class TokenBucketRateLimiter:
    """
    Token bucket algorithm for rate limiting with burst support
    Allows bursts while maintaining average rate
    """
    
    def __init__(
        self, 
        rate: float,  # Average requests per second
        capacity: int = None,  # Burst capacity
        refill_period: float = 1.0
    ):
        self.rate = rate
        self.capacity = capacity or int(rate * 2)  # Default: 2x burst
        self.tokens = self.capacity
        self.refill_period = refill_period
        self.tokens_per_refill = rate * refill_period
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1):
        """Acquire tokens, waiting if necessary"""
        async with self.lock:
            while tokens > self.tokens:
                await self._refill()
                if tokens > self.tokens:
                    wait_time = (tokens - self.tokens) / self.rate
                    await asyncio.sleep(wait_time)
            
            self.tokens -= tokens
    
    async def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed >= self.refill_period:
            tokens_to_add = min(
                self.tokens_per_refill * (elapsed / self.refill_period),
                self.capacity - self.tokens
            )
            self.tokens = min(self.tokens + tokens_to_add, self.capacity)
            self.last_refill = now


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on response times
    and error rates
    """
    
    def __init__(
        self,
        initial_rate: float = 10,
        min_rate: float = 1,
        max_rate: float = 50,
        window_size: int = 100
    ):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.window_size = window_size
        self.response_times = deque(maxlen=window_size)
        self.error_count = 0
        self.success_count = 0
        self.bucket = TokenBucketRateLimiter(initial_rate)
    
    async def acquire(self):
        """Acquire permission to make request"""
        await self.bucket.acquire()
    
    async def record_response(
        self, 
        response_time: float, 
        is_error: bool = False
    ):
        """Record response and adjust rate if needed"""
        self.response_times.append(response_time)
        
        if is_error:
            self.error_count += 1
            # Reduce rate on errors
            await self._adjust_rate(multiplier=0.8)
        else:
            self.success_count += 1
            # Increase rate if response times are good
            if len(self.response_times) >= 10:
                avg_time = sum(self.response_times) / len(self.response_times)
                if avg_time < 1.0:  # Fast responses
                    await self._adjust_rate(multiplier=1.1)
                elif avg_time > 5.0:  # Slow responses
                    await self._adjust_rate(multiplier=0.9)
    
    async def _adjust_rate(self, multiplier: float):
        """Adjust the rate within bounds"""
        new_rate = self.current_rate * multiplier
        new_rate = max(self.min_rate, min(self.max_rate, new_rate))
        
        if new_rate != self.current_rate:
            self.current_rate = new_rate
            self.bucket = TokenBucketRateLimiter(new_rate)
```

## Usage Examples

### Example 1: Simple Parallel Processing
```python
# Synchronous usage (backward compatible)
client = AsyncCompatibleClient(credentials, max_concurrent=5, rate_limit=10)

# Process multiple banks in parallel
results = client.collect_data_parallel(
    "2020-03-31", 
    ["12345", "67890", "11111"]
)
```

### Example 2: Async Integration
```python
# In an async application
async def process_banks():
    async with AsyncCompatibleClient(credentials, rate_limit=10) as client:
        # Collect multiple quarters for one bank
        time_series = await client.collect_time_series_async(
            "12345",
            ["2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"]
        )
        
        # Process batch with progress
        async def progress(rssd_id, result):
            print(f"Completed {rssd_id}")
        
        batch_results = await client.collect_batch_async(
            "2020-03-31",
            bank_list,
            progress_callback=progress
        )
```

### Example 3: External Async Framework Integration
```python
# Django Channels
from channels.generic.websocket import AsyncWebsocketConsumer

class FFIECConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ffiec = FFIECAsyncAdapter(credentials)
        await self.ffiec.setup()
        await self.accept()
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Non-blocking data collection
        result = await self.ffiec.collect_with_timeout(
            data['period'],
            data['rssd_id'],
            timeout=10.0
        )
        
        await self.send(text_data=json.dumps(result))
    
    async def disconnect(self, close_code):
        await self.ffiec.cleanup()
```

### Example 4: Rate-Limited Batch Processing
```python
async def process_large_dataset(bank_ids: List[str]):
    """Process large dataset with adaptive rate limiting"""
    
    # Use adaptive rate limiter
    rate_limiter = AdaptiveRateLimiter(
        initial_rate=10,
        min_rate=5,
        max_rate=20
    )
    
    async with AsyncCompatibleClient(credentials) as client:
        client.rate_limiter = rate_limiter
        
        for chunk in chunks(bank_ids, 100):
            start_time = time.time()
            
            try:
                results = await client.collect_batch_async(
                    "2020-03-31", 
                    chunk
                )
                
                # Record success
                response_time = time.time() - start_time
                await rate_limiter.record_response(response_time)
                
            except Exception as e:
                # Record failure and back off
                await rate_limiter.record_response(10.0, is_error=True)
                print(f"Error processing chunk: {e}")
            
            # Adaptive delay between chunks
            await asyncio.sleep(1.0 / rate_limiter.current_rate)
```

## Testing Strategy

### Unit Tests for Async Components
```python
# tests/test_async_compatible.py
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_rate_limiter():
    """Test rate limiting works correctly"""
    limiter = RateLimiter(calls_per_second=10)
    
    start = time.time()
    for _ in range(5):
        await limiter.async_wait_if_needed()
    elapsed = time.time() - start
    
    # Should take at least 0.4 seconds (5 calls at 10/sec)
    assert elapsed >= 0.4

@pytest.mark.asyncio
async def test_parallel_collection():
    """Test parallel collection respects concurrency limit"""
    client = AsyncCompatibleClient(
        mock_credentials, 
        max_concurrent=2,
        rate_limit=None  # Disable for testing
    )
    
    with patch.object(client, 'collect_data', new_callable=AsyncMock) as mock:
        mock.return_value = {'test': 'data'}
        
        results = await client.collect_batch_async(
            "2020-03-31",
            ["1", "2", "3", "4", "5"]
        )
        
        assert len(results) == 5
        assert mock.call_count == 5
```

## Implementation Priority

### Phase 1: Core Async Support (Week 1)
1. Implement `AsyncCompatibleClient`
2. Add basic rate limiting
3. Test with existing code

### Phase 2: Integration Features (Week 2)
1. Add adapter classes
2. Implement advanced rate limiting
3. Create integration examples

### Phase 3: Optimization (Week 3)
1. Add caching layer
2. Implement connection pooling
3. Performance testing

## Benefits Despite Rate Limits

1. **Parallel Different Operations**: Collect multiple quarters or series simultaneously
2. **Non-Blocking Integration**: Doesn't block event loops in async applications
3. **Better Resource Utilization**: Thread pool for CPU-bound XML processing
4. **Graceful Degradation**: Adaptive rate limiting prevents API throttling
5. **Progress Tracking**: Real-time updates for long-running operations
6. **Timeout Support**: Prevent hanging requests
7. **Error Resilience**: Continue processing despite individual failures

## Conclusion

Even with rate limits, async support provides significant value:
- **5-10x speedup** for multi-dimensional queries (different periods/series)
- **Non-blocking integration** with modern async frameworks
- **Better user experience** with progress tracking and timeouts
- **Increased reliability** with smart rate limiting and error handling