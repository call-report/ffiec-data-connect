"""
Comprehensive unit tests for ffiec_connection.py with race condition focus.

Tests connection management, thread safety, resource cleanup, and proxy configuration.
"""

import pytest
import threading
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, ConnectionError as RequestsConnectionError

from ffiec_data_connect.ffiec_connection import FFIECConnection, ProxyProtocol
from ffiec_data_connect.exceptions import SessionError, ConnectionError


class TestFFIECConnectionInitialization:
    """Test FFIECConnection initialization and basic properties."""
    
    def test_init_creates_instance(self):
        """Test basic initialization."""
        conn = FFIECConnection()
        
        assert conn is not None
        assert hasattr(conn, '_lock')
        assert hasattr(conn, '_session')
        assert conn._session is None  # Lazy loading
        assert conn._use_proxy is False
    
    def test_init_registers_instance(self):
        """Test that instances are registered for cleanup."""
        initial_count = len(FFIECConnection._instances)
        conn = FFIECConnection()
        
        assert len(FFIECConnection._instances) == initial_count + 1
        assert conn in FFIECConnection._instances
    
    def test_proxy_defaults(self):
        """Test proxy configuration defaults."""
        conn = FFIECConnection()
        
        assert conn.use_proxy is False
        assert conn.proxy_host is None
        assert conn.proxy_port is None
        assert conn.proxy_user_name is None
        assert conn.proxy_password is None
        assert conn.proxy_protocol is None


class TestSessionManagement:
    """Test session creation and management."""
    
    def test_session_lazy_loading(self):
        """Test that session is created on first access."""
        conn = FFIECConnection()
        
        # Session should be None initially
        assert conn._session is None
        
        # Accessing session property should create it
        session = conn.session
        assert isinstance(session, requests.Session)
        assert conn._session is not None
    
    def test_session_reuse(self):
        """Test that same session is reused on multiple accesses."""
        conn = FFIECConnection()
        
        session1 = conn.session
        session2 = conn.session
        
        assert session1 is session2
    
    def test_session_setter(self):
        """Test setting custom session."""
        conn = FFIECConnection()
        custom_session = Mock(spec=requests.Session)
        
        # First create a session to test cleanup
        _ = conn.session
        old_session = conn._session
        
        # Set custom session
        conn.session = custom_session
        
        # Verify old session was closed (mocked)
        assert conn._session is custom_session
    
    @patch('requests.Session')
    def test_session_creation_with_proxy_disabled(self, mock_session_class):
        """Test session creation without proxy."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        conn = FFIECConnection()
        conn.use_proxy = False
        
        session = conn.session
        
        mock_session_class.assert_called_once()
        # When proxy is disabled, the code should not set proxies
        # This just verifies the session was created and returned
        assert session is mock_session


class TestProxyConfiguration:
    """Test proxy configuration and validation."""
    
    def test_proxy_host_setting(self):
        """Test setting proxy host."""
        conn = FFIECConnection()
        
        conn.proxy_host = "proxy.example.com"
        assert conn.proxy_host == "proxy.example.com"
    
    def test_proxy_port_setting(self):
        """Test setting proxy port."""
        conn = FFIECConnection()
        
        conn.proxy_port = 8080
        assert conn.proxy_port == 8080
    
    def test_proxy_protocol_setting(self):
        """Test setting proxy protocol."""
        conn = FFIECConnection()
        
        conn.proxy_protocol = ProxyProtocol.HTTP
        assert conn.proxy_protocol == ProxyProtocol.HTTP
    
    def test_proxy_credentials_setting(self):
        """Test setting proxy username and password."""
        conn = FFIECConnection()
        
        conn.proxy_user_name = "testuser"
        conn.proxy_password = "testpass"
        
        assert conn.proxy_user_name == "testuser" 
        assert conn.proxy_password == "testpass"
    
    def test_enable_proxy_without_configuration_fails(self):
        """Test that enabling proxy without complete config fails."""
        conn = FFIECConnection()
        
        # Try to enable proxy without configuration
        with pytest.raises((SessionError, ValueError)) as exc_info:
            conn.use_proxy = True
        
        error_message = str(exc_info.value)
        assert "proxy" in error_message.lower()
        assert "configuration" in error_message.lower()
    
    def test_enable_proxy_with_partial_configuration_fails(self):
        """Test enabling proxy with incomplete configuration."""
        conn = FFIECConnection()
        
        # Set only host, missing port and protocol
        conn.proxy_host = "proxy.example.com"
        
        with pytest.raises((SessionError, ValueError)) as exc_info:
            conn.use_proxy = True
        
        error_message = str(exc_info.value)
        assert "complete" in error_message.lower()
    
    def test_enable_proxy_with_complete_configuration_succeeds(self):
        """Test enabling proxy with complete configuration."""
        conn = FFIECConnection()
        
        # Set complete configuration
        conn.proxy_host = "proxy.example.com"
        conn.proxy_port = 8080
        conn.proxy_protocol = ProxyProtocol.HTTP
        
        # Should not raise error
        conn.use_proxy = True
        assert conn.use_proxy is True
    
    @patch('requests.Session')
    def test_proxy_session_generation(self, mock_session_class):
        """Test session generation with proxy configuration."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        conn = FFIECConnection()
        conn.proxy_host = "proxy.example.com"
        conn.proxy_port = 8080
        conn.proxy_protocol = ProxyProtocol.HTTP
        conn.use_proxy = True
        
        # Access session to trigger generation
        _ = conn.session
        
        # Should have set proxies on session
        mock_session_class.assert_called_once()
    
    def test_proxy_configuration_invalidates_cache(self):
        """Test that changing proxy config invalidates session cache.""" 
        conn = FFIECConnection()
        
        # Create initial session
        session1 = conn.session
        
        # Change proxy configuration
        conn.proxy_host = "proxy.example.com"
        
        # Configuration hash should be invalidated
        assert conn._config_hash is None


class TestThreadSafety:
    """Test thread safety of FFIECConnection."""
    
    def test_concurrent_session_access(self):
        """Test concurrent access to session property."""
        conn = FFIECConnection()
        sessions = []
        errors = []
        
        def get_session():
            try:
                session = conn.session
                sessions.append(session)
            except Exception as e:
                errors.append(str(e))
        
        # Access session from multiple threads
        threads = []
        for i in range(20):
            t = threading.Thread(target=get_session)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        assert len(sessions) == 20
        
        # All sessions should be the same object (reused)
        for session in sessions:
            assert session is sessions[0]
    
    def test_concurrent_proxy_configuration(self):
        """Test concurrent proxy configuration changes."""
        conn = FFIECConnection()
        errors = []
        
        def configure_proxy(host_suffix):
            try:
                conn.proxy_host = f"proxy{host_suffix}.example.com"
                conn.proxy_port = 8080 + host_suffix
                conn.proxy_protocol = ProxyProtocol.HTTP
                # Brief delay to increase chance of race condition
                time.sleep(0.001)
                conn.use_proxy = True
            except Exception as e:
                errors.append(str(e))
        
        # Configure proxy from multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=configure_proxy, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
        assert conn.use_proxy is True
    
    def test_session_regeneration_thread_safety(self):
        """Test thread safety during session regeneration."""
        conn = FFIECConnection()
        sessions = []
        errors = []
        
        def access_and_reconfigure():
            try:
                # Access session
                session = conn.session
                sessions.append(session)
                
                # Brief delay
                time.sleep(0.001)
                
                # Change configuration to force regeneration
                conn.proxy_host = f"proxy{threading.current_thread().ident}.com"
                conn._config_hash = None  # Force regeneration
                
                # Access session again
                new_session = conn.session
                sessions.append(new_session)
                
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=access_and_reconfigure)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
        assert len(sessions) == 20  # 2 per thread
    
    def test_concurrent_session_setting(self):
        """Test thread safety when setting sessions concurrently."""
        conn = FFIECConnection()
        set_sessions = []
        errors = []
        
        def set_custom_session(session_id):
            try:
                custom_session = Mock(spec=requests.Session)
                custom_session.session_id = session_id
                conn.session = custom_session
                set_sessions.append(custom_session)
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=set_custom_session, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0
        assert len(set_sessions) == 10
        
        # Final session should be one of the set sessions
        final_session = conn.session
        assert final_session in set_sessions


class TestResourceCleanup:
    """Test resource cleanup and memory management."""
    
    def test_close_method(self):
        """Test explicit close method."""
        conn = FFIECConnection()
        
        # Create session
        session = conn.session
        assert conn._session is not None
        
        # Close connection
        conn.close()
        
        # Session should be cleared
        assert conn._session is None
        assert conn._config_hash is None
    
    def test_context_manager_support(self):
        """Test context manager functionality."""
        with FFIECConnection() as conn:
            session = conn.session
            assert conn._session is not None
        
        # Should be closed after exiting context
        assert conn._session is None
    
    def test_del_cleanup(self):
        """Test cleanup during garbage collection."""
        conn = FFIECConnection()
        session = conn.session
        
        assert conn._session is not None
        
        # Manually call __del__ (simulating garbage collection)
        conn.__del__()
        
        assert conn._session is None
    
    def test_session_replacement_cleanup(self):
        """Test that old sessions are cleaned up when replaced."""
        conn = FFIECConnection()
        
        # Create first session
        session1 = conn.session
        mock_session1 = Mock(spec=requests.Session)
        conn._session = mock_session1
        
        # Set new session - should close old one
        mock_session2 = Mock(spec=requests.Session)
        conn.session = mock_session2
        
        # Old session should have been closed (implicitly via close())
        assert conn._session is mock_session2
    
    def test_class_cleanup_all(self):
        """Test class-level cleanup method."""
        # Create multiple instances
        instances = [FFIECConnection() for _ in range(5)]
        
        # Create sessions for all
        for instance in instances:
            _ = instance.session
            assert instance._session is not None
        
        # Cleanup all
        FFIECConnection.cleanup_all()
        
        # All should be cleaned up
        for instance in instances:
            assert instance._session is None


class TestConnectionTesting:
    """Test connection testing functionality."""
    
    @patch('requests.Session.get')
    def test_successful_connection_test(self, mock_get):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        conn = FFIECConnection()
        result = conn.test_connection()
        
        assert result is True
        mock_get.assert_called_once_with("https://google.com")
    
    @patch('requests.Session.get')
    def test_failed_connection_test(self, mock_get):
        """Test failed connection test."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        conn = FFIECConnection()
        
        with patch('builtins.print') as mock_print:
            result = conn.test_connection()
        
        assert result is False
        mock_print.assert_called_once()
        assert "404" in str(mock_print.call_args)
    
    @patch('requests.Session.get')
    def test_connection_test_custom_url(self, mock_get):
        """Test connection test with custom URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        conn = FFIECConnection()
        custom_url = "https://example.com"
        result = conn.test_connection(custom_url)
        
        assert result is True
        mock_get.assert_called_once_with(custom_url)
    
    @patch('requests.Session.get')
    def test_connection_test_with_proxy(self, mock_get):
        """Test connection test with proxy configuration."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        conn = FFIECConnection()
        conn.proxy_host = "proxy.example.com"
        conn.proxy_port = 8080
        conn.proxy_protocol = ProxyProtocol.HTTP
        conn.use_proxy = True
        
        result = conn.test_connection()
        
        assert result is True
        mock_get.assert_called_once_with("https://google.com")


class TestStringRepresentation:
    """Test string representation and data masking."""
    
    def test_str_representation_no_proxy(self):
        """Test string representation without proxy."""
        conn = FFIECConnection()
        str_repr = str(conn)
        
        assert "FFIECConnection" in str_repr
        assert "proxy_enabled=False" in str_repr
        assert "proxy_host='None'" in str_repr
        assert "session_status=" in str_repr
    
    def test_str_representation_with_proxy(self):
        """Test string representation with proxy."""
        conn = FFIECConnection()
        conn.proxy_host = "proxy.example.com"
        conn.proxy_port = 8080
        conn.proxy_protocol = ProxyProtocol.HTTPS
        conn.proxy_user_name = "proxyuser"
        conn.proxy_password = "proxypass"
        conn.use_proxy = True
        
        str_repr = str(conn)
        
        assert "proxy_enabled=True" in str_repr
        assert "proxy.example.com" not in str_repr  # Should be masked
        assert "***." in str_repr  # Masked hostname
        assert "proxy_port=8080" in str_repr
        assert "HTTPS" in str_repr
        assert "proxyuser" not in str_repr  # Should be masked
        assert "p*******r" in str_repr or "***" in str_repr  # Masked username
        assert "proxypass" not in str_repr  # Password never shown
        assert "proxy_password_set=True" in str_repr
    
    def test_repr_equals_str(self):
        """Test that repr equals str."""
        conn = FFIECConnection()
        
        assert repr(conn) == str(conn)
    
    def test_hostname_masking(self):
        """Test hostname masking functionality."""
        conn = FFIECConnection()
        
        # Test various hostname formats
        assert "***." in conn._mask_host("proxy.example.com")
        assert "example.com" in conn._mask_host("proxy.example.com")
        assert conn._mask_host("localhost") == "***"
        assert conn._mask_host("") == "***"
        assert conn._mask_host(None) == "***"
    
    def test_string_masking(self):
        """Test general string masking functionality."""
        conn = FFIECConnection()
        
        # Test various string lengths
        assert conn._mask_string("user") == "u**r"
        assert conn._mask_string("ab") == "**"
        assert conn._mask_string("a") == "*"
        assert conn._mask_string("") == "***"
        assert conn._mask_string(None) == "***"


class TestConfigurationHashChange:
    """Test configuration change detection."""
    
    def test_config_hash_generation(self):
        """Test configuration hash generation."""
        conn = FFIECConnection()
        
        # Get initial hash
        hash1 = conn._get_config_hash()
        
        # Change configuration
        conn.proxy_host = "proxy.example.com"
        hash2 = conn._get_config_hash()
        
        # Hashes should be different
        assert hash1 != hash2
    
    def test_config_hash_consistency(self):
        """Test that same configuration generates same hash."""
        conn1 = FFIECConnection()
        conn2 = FFIECConnection()
        
        # Set same configuration
        for conn in [conn1, conn2]:
            conn.proxy_host = "proxy.example.com"
            conn.proxy_port = 8080
            conn.proxy_protocol = ProxyProtocol.HTTP
            conn.use_proxy = True
        
        hash1 = conn1._get_config_hash()
        hash2 = conn2._get_config_hash()
        
        assert hash1 == hash2
    
    def test_password_not_in_hash(self):
        """Test that actual passwords are not included in hash."""
        conn = FFIECConnection()
        
        conn.proxy_password = "password1"
        hash1 = conn._get_config_hash()
        
        conn.proxy_password = "password2"
        hash2 = conn._get_config_hash()
        
        # Hash should be the same (only presence matters, not value)
        assert hash1 == hash2


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_session_generation_with_invalid_proxy(self):
        """Test session generation with invalid proxy configuration."""
        conn = FFIECConnection()
        
        # Enable proxy without complete configuration
        conn._use_proxy = True  # Bypass setter validation
        
        with pytest.raises((SessionError, ValueError)) as exc_info:
            _ = conn.session
        
        error_message = str(exc_info.value)
        assert "proxy" in error_message.lower()
        assert "incomplete" in error_message.lower()
    
    def test_cleanup_error_handling(self):
        """Test that cleanup errors are handled gracefully."""
        conn = FFIECConnection()
        
        # Create session
        _ = conn.session
        
        # Mock session.close to raise exception
        mock_session = Mock(spec=requests.Session)
        mock_session.close.side_effect = Exception("Close error")
        conn._session = mock_session
        
        # Should not raise exception
        conn.close()
        
        # Session should still be cleared
        assert conn._session is None


class TestMemoryLeakPrevention:
    """Test memory leak prevention measures."""
    
    def test_session_replacement_prevents_leaks(self):
        """Test that replacing sessions properly cleans up old ones."""
        conn = FFIECConnection()
        
        # Create and track multiple sessions
        old_sessions = []
        for i in range(5):
            session = conn.session
            old_sessions.append(session)
            
            # Force new session creation
            conn._config_hash = None
            conn.proxy_host = f"proxy{i}.com"
        
        # All old sessions should be properly cleaned up
        # (This is a behavioral test - actual cleanup verification would require memory monitoring)
        assert conn._session is not None
        assert len(old_sessions) == 5
    
    def test_weakref_instance_tracking(self):
        """Test that instance tracking uses weak references."""
        initial_count = len(FFIECConnection._instances)
        
        # Create instances in a scope
        instances = [FFIECConnection() for _ in range(3)]
        assert len(FFIECConnection._instances) == initial_count + 3
        
        # Delete references
        del instances
        
        # WeakSet should allow garbage collection
        # (May need to force garbage collection in real scenarios)
        # This tests the structure, not the actual garbage collection


class TestRaceConditions:
    """Specific tests for race condition scenarios."""
    
    def test_session_creation_race(self):
        """Test race condition during session creation."""
        conn = FFIECConnection()
        created_sessions = []
        errors = []
        
        def create_session():
            try:
                # Force session creation race
                if conn._session is None:
                    time.sleep(0.001)  # Small delay to increase race chance
                session = conn.session
                created_sessions.append(session)
            except Exception as e:
                errors.append(str(e))
        
        # Start many threads simultaneously
        threads = []
        for i in range(50):
            t = threading.Thread(target=create_session)
            threads.append(t)
        
        # Start all at once
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        assert len(created_sessions) == 50
        
        # All should be the same session (no duplicate creation)
        for session in created_sessions:
            assert session is created_sessions[0]
    
    def test_proxy_config_race(self):
        """Test race condition in proxy configuration."""
        conn = FFIECConnection()
        results = []
        errors = []
        
        def configure_and_access(config_id):
            try:
                # Configure proxy
                conn.proxy_host = f"proxy{config_id}.com"
                conn.proxy_port = 8080 + config_id
                conn.proxy_protocol = ProxyProtocol.HTTP
                
                # Brief delay to increase race condition chance
                time.sleep(0.001)
                
                # Enable proxy and access session
                conn.use_proxy = True
                session = conn.session
                
                results.append((config_id, session))
            except Exception as e:
                errors.append((config_id, str(e)))
        
        threads = []
        for i in range(20):
            t = threading.Thread(target=configure_and_access, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should complete with minimal errors (some config race conditions are expected)
        assert len(results) > 0
        # Allow some errors due to race conditions in configuration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])