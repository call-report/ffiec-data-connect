# Race Condition Analysis - FFIEC Data Connect

## Executive Summary
This analysis examines the FFIEC Data Connect Python library for potential race conditions and thread safety issues. The review focuses on shared state management, concurrent access patterns, and synchronization mechanisms.

**Review Date:** August 7, 2025  
**Repository:** ffiec-data-connect  
**Version Reviewed:** 0.2.7  
**Overall Thread Safety Assessment:** HIGH RISK - Not Thread-Safe

## Critical Findings

### 1. FFIECConnection Class - Critical Race Conditions
**Location:** `src/ffiec_data_connect/ffiec_connection.py`

#### Issue: Session Regeneration During Property Updates
The `FFIECConnection` class has a severe race condition pattern where setting any proxy-related property triggers a complete session regeneration:

```python
@proxy_host.setter
def proxy_host(self, host: str) -> None:
    self._generate_session()  # Line 86 - Regenerates session
    self._proxy_host = host    # Line 88 - Then sets the value
```

**Race Condition Scenarios:**
1. **Thread A** sets `proxy_host` → triggers `_generate_session()`
2. **Thread B** sets `proxy_port` → triggers `_generate_session()` 
3. **Thread A** completes setting `_proxy_host`
4. Session is now inconsistent with partial proxy configuration

**Impact:** 
- Session object can be in an inconsistent state
- Proxy configuration may be partially applied
- Active requests may fail or use wrong proxy settings

#### Issue: Check-Then-Act Pattern in Session Generation
**Location:** `src/ffiec_data_connect/ffiec_connection.py:231-242`

```python
if self.use_proxy:
    if self.proxy_host is None or self.proxy_port is None:  # Check
        raise()
    # Gap where another thread could modify proxy settings
    session.proxies = {...}  # Act
```

**Race Condition:** Time-of-check to time-of-use (TOCTOU) vulnerability where proxy settings could change between validation and use.

### 2. WebserviceCredentials Class - Moderate Risk
**Location:** `src/ffiec_data_connect/credentials.py`

#### Issue: Unprotected Credential Updates
Properties can be modified during authentication:

```python
@username.setter
def username(self, username: str) -> None:
    self._username = username  # No synchronization
```

**Race Condition Scenario:**
1. **Thread A** calls `test_credentials()` with username "user1"
2. **Thread B** changes username to "user2" mid-authentication
3. Authentication may fail or use mixed credentials

### 3. Module-Level Variables - Low to Moderate Risk
**Location:** `src/ffiec_data_connect/methods.py:19-24`

```python
quarterStringRegex = r"^[1-4](q|Q)([0-9]{4})$"
yyyymmddRegex = r"^[0-9]{4}[0-9]{2}[0-9]{2}$"
validRegexList = [...]
```

**Issue:** While these are read-only after initialization, if any code were to modify these patterns, all threads would be affected.

### 4. SOAP Client Creation - Moderate Risk
**Location:** `src/ffiec_data_connect/methods.py`

#### Issue: New Client Per Request
Each API call creates a new SOAP client:

```python
def collect_data(...):
    client = _client_factory(session, creds)  # New client each time
    ret = client.service.RetrieveFacsimile(...)
```

**Implications:**
- No client reuse means no shared client state (good for thread safety)
- However, inefficient for multiple concurrent requests
- Session object is shared but clients are not

## Detailed Analysis by Component

### Session Management
The `requests.Session` object is shared across operations but modified during runtime:

**Problems:**
1. Session is regenerated on every proxy setting change
2. No synchronization around session access
3. Session.proxies dictionary is modified directly

**Example Race Condition:**
```python
# Thread 1
connection.proxy_host = "proxy1.example.com"
# Triggers _generate_session()

# Thread 2 (simultaneously)
response = connection.session.get("https://api.example.com")
# May use old or partially configured session
```

### Property Setter Anti-Pattern
Multiple properties trigger side effects:

```python
# Each of these regenerates the session:
connection.proxy_host = "..."     # Regenerates session
connection.proxy_port = 8080      # Regenerates session again
connection.proxy_user_name = "..." # Regenerates session again
connection.use_proxy = True       # Regenerates session again
```

**Impact:** Four session regenerations for one logical proxy configuration update.

### XML Processing
**Location:** `src/ffiec_data_connect/xbrl_processor.py`

The XML processing uses a compiled regex at module level:
```python
re_date = re.compile('[0-9]{4}\-[0-9]{2}\-[0-9]{2}')
```

**Assessment:** Safe as compiled regex objects are thread-safe for matching operations.

## Race Condition Risk Matrix

| Component | Risk Level | Likelihood | Impact | Thread-Safe |
|-----------|------------|------------|---------|-------------|
| FFIECConnection._generate_session() | Critical | High | High | No |
| FFIECConnection property setters | Critical | High | High | No |
| WebserviceCredentials properties | Moderate | Medium | Medium | No |
| Session.proxies modification | High | High | High | No |
| SOAP client creation | Low | Low | Low | Yes* |
| Module-level regex patterns | Low | Low | Low | Yes |
| XML processing | Low | Low | Low | Yes |

*Each request creates new client, avoiding shared state

## Exploitation Scenarios

### Scenario 1: Proxy Configuration Corruption
```python
# Thread 1: Configure proxy for internal network
connection.proxy_host = "internal-proxy.company.com"
connection.proxy_port = 8080
connection.proxy_user_name = "internal_user"
connection.proxy_password = "internal_pass"

# Thread 2: Configure proxy for external network (simultaneous)
connection.proxy_host = "external-proxy.company.com"
connection.proxy_port = 3128
connection.proxy_user_name = "external_user"
connection.proxy_password = "external_pass"

# Result: Mixed configuration, potential credential leakage
```

### Scenario 2: Authentication Race
```python
# Thread 1: Authenticate with user1
creds.username = "user1"
creds.password = "pass1"
creds.test_credentials(session)

# Thread 2: Change credentials mid-authentication
creds.username = "user2"
creds.password = "pass2"

# Result: Authentication failure or wrong user authenticated
```

## Recommendations

### Immediate Fixes

#### 1. Implement Thread-Safe Proxy Configuration
```python
import threading

class FFIECConnection:
    def __init__(self):
        self._lock = threading.RLock()
        # ... rest of init
    
    def update_proxy_config(self, host=None, port=None, 
                           username=None, password=None, 
                           protocol=None, use_proxy=None):
        """Atomic proxy configuration update"""
        with self._lock:
            if host is not None:
                self._proxy_host = host
            if port is not None:
                self._proxy_port = port
            # ... update all settings
            self._generate_session()  # Regenerate once
```

#### 2. Make Credentials Immutable
```python
class WebserviceCredentials:
    def __init__(self, username=None, password=None):
        self._username = username
        self._password = password
        # Remove setters - make immutable
    
    @property
    def username(self):
        return self._username
    
    # No setter - credentials are immutable after creation
```

#### 3. Implement Session Locking
```python
class FFIECConnection:
    def _generate_session(self):
        with self._lock:
            # Generate session with thread safety
            session = requests.Session()
            # ... configure session
            self._session = session
```

### Long-term Improvements

#### 1. Connection Pool Pattern
Implement a thread-safe connection pool:
```python
class ConnectionPool:
    def __init__(self, size=10):
        self._pool = queue.Queue(maxsize=size)
        self._lock = threading.Lock()
    
    def get_connection(self):
        return self._pool.get()
    
    def return_connection(self, conn):
        self._pool.put(conn)
```

#### 2. Builder Pattern for Configuration
```python
class FFIECConnectionBuilder:
    def with_proxy(self, host, port):
        self.proxy_host = host
        self.proxy_port = port
        return self
    
    def build(self):
        # Create immutable connection with all settings
        return FFIECConnection(self._config)
```

#### 3. Async/Await Support
Consider adding async support for better concurrency:
```python
import aiohttp

async def collect_data_async(session, creds, **kwargs):
    async with aiohttp.ClientSession() as session:
        # Async implementation
        pass
```

## Testing Recommendations

### Race Condition Tests
```python
import threading
import time

def test_proxy_configuration_race():
    connection = FFIECConnection()
    errors = []
    
    def configure_proxy_1():
        try:
            connection.proxy_host = "proxy1.com"
            time.sleep(0.001)
            connection.proxy_port = 8080
            assert connection.proxy_host == "proxy1.com"
        except Exception as e:
            errors.append(e)
    
    def configure_proxy_2():
        try:
            connection.proxy_host = "proxy2.com"
            time.sleep(0.001)
            connection.proxy_port = 3128
            assert connection.proxy_host == "proxy2.com"
        except Exception as e:
            errors.append(e)
    
    threads = [
        threading.Thread(target=configure_proxy_1),
        threading.Thread(target=configure_proxy_2)
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Race condition detected: {errors}"
```

## Usage Guidelines for Thread Safety

### Current State - NOT THREAD-SAFE
**Do not use this library in multi-threaded applications without modifications.**

### Safe Usage Patterns (Workarounds)

#### 1. Thread-Local Storage
```python
import threading

thread_local = threading.local()

def get_connection():
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = FFIECConnection()
    return thread_local.connection
```

#### 2. Separate Instances Per Thread
```python
def worker_thread(thread_id):
    # Each thread creates its own connection
    connection = FFIECConnection()
    creds = WebserviceCredentials()
    # Use connection only in this thread
```

#### 3. External Synchronization
```python
import threading

connection_lock = threading.Lock()

def safe_api_call():
    with connection_lock:
        connection = FFIECConnection()
        # Perform API call
        result = methods.collect_data(...)
    return result
```

## Conclusion

The FFIEC Data Connect library has significant thread safety issues that make it unsuitable for multi-threaded use without modifications. The primary concerns are:

1. **Session regeneration race conditions** in FFIECConnection
2. **Mutable shared state** without synchronization
3. **Property setter side effects** causing cascading state changes

These issues can lead to:
- Data corruption
- Authentication failures  
- Incorrect proxy routing
- Unpredictable behavior in concurrent environments

**Recommendation:** The library should be refactored with thread safety in mind, implementing proper synchronization mechanisms or adopting an immutable design pattern. Until then, users should ensure single-threaded access or implement external synchronization.

## Severity Assessment

**Overall Risk:** HIGH
- **Exploitability:** Easy (standard multi-threading triggers issues)
- **Impact:** High (data corruption, security credential mixing)
- **Likelihood:** High (any multi-threaded use will encounter issues)
- **Mitigation Difficulty:** Moderate (requires significant refactoring)