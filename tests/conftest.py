"""
Pytest configuration and shared fixtures for FFIEC Data Connect tests.

This module provides common test fixtures and configuration for the test suite.
"""

import pytest
import os
import warnings
from unittest.mock import Mock, patch
from typing import Generator

# Import for fixture creation
import ffiec_data_connect
from ffiec_data_connect import WebserviceCredentials, FFIECConnection
from ffiec_data_connect.config import Config


@pytest.fixture(autouse=True)
def reset_config_after_test():
    """Automatically reset configuration after each test to prevent test interference."""
    yield
    # Reset to default state after each test
    Config.reset()


@pytest.fixture
def suppress_deprecation_warnings():
    """Suppress deprecation warnings for legacy mode in tests where they're not relevant."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="ffiec_data_connect")
        yield


@pytest.fixture
def mock_credentials() -> WebserviceCredentials:
    """Create mock credentials for testing without real auth."""
    with patch.dict(os.environ, {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
        return WebserviceCredentials()


@pytest.fixture
def mock_connection() -> FFIECConnection:
    """Create a mock FFIECConnection for testing."""
    return FFIECConnection()


@pytest.fixture
def mock_soap_response():
    """Mock SOAP response data for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <cc:test_item contextRef="test" unitRef="test" decimals="0">12345</cc:test_item>
</xbrl>"""


@pytest.fixture
def sample_xbrl_data():
    """Sample XBRL data for XML processing tests."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" 
      xmlns:cc="http://www.ffiec.gov/call" 
      xmlns:uc="http://www.ffiec.gov/call/uc">
    <cc:RCON0010 contextRef="c1" unitRef="u1" decimals="0">1000000</cc:RCON0010>
    <cc:RCON0071 contextRef="c1" unitRef="u1" decimals="0">500000</cc:RCON0071>
    <uc:UBPR4107 contextRef="c1" unitRef="u1" decimals="2">12.50</uc:UBPR4107>
</xbrl>"""


@pytest.fixture
def legacy_mode_enabled():
    """Enable legacy error mode for the duration of the test."""
    original_state = Config.use_legacy_errors()
    Config.set_legacy_errors(True)
    Config._deprecation_warning_shown = True  # Suppress warning in tests
    yield
    Config.set_legacy_errors(original_state)


@pytest.fixture
def legacy_mode_disabled():
    """Disable legacy error mode for the duration of the test."""
    original_state = Config.use_legacy_errors()
    Config.set_legacy_errors(False)
    yield
    Config.set_legacy_errors(original_state)


@pytest.fixture
def mock_session():
    """Create a mock requests session for testing."""
    from unittest.mock import Mock
    session = Mock()
    session.get.return_value.status_code = 200
    session.post.return_value.status_code = 200
    return session


@pytest.fixture
def mock_soap_client():
    """Create a mock SOAP client for testing."""
    mock_client = Mock()
    mock_client.service.TestUserAccess.return_value = True
    mock_client.service.RetrieveReportingPeriods.return_value = [
        "2023-03-31", "2023-06-30", "2023-09-30", "2023-12-31"
    ]
    mock_client.service.RetrieveFacsimile.return_value = b"mock xbrl data"
    return mock_client


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    import pathlib
    return pathlib.Path(__file__).parent / "fixtures"


# Configure pytest-asyncio for async tests
pytest_plugins = ['pytest_asyncio']


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security-related"
    )
    config.addinivalue_line(
        "markers", "race_condition: marks tests for race condition scenarios"
    )
    config.addinivalue_line(
        "markers", "memory_leak: marks tests for memory leak detection"
    )
    config.addinivalue_line(
        "markers", "async_test: marks tests for async functionality"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Auto-mark tests based on directory structure
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Auto-mark async tests
        if "async" in item.name or "async" in str(item.fspath):
            item.add_marker(pytest.mark.async_test)


# Global test configuration
def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    print("\n🧪 Starting FFIEC Data Connect test suite...")
    
    # Ensure clean state for tests
    Config.reset()


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    if exitstatus == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Test suite finished with exit status: {exitstatus}")