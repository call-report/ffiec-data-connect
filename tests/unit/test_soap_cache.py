"""
Test SOAP client caching functionality.

Tests that SOAP clients are properly cached for performance optimization.
"""

import pytest
from unittest.mock import Mock, patch

from ffiec_data_connect.soap_cache import (
    SOAPClientConfig, 
    SOAPClientCache, 
    get_soap_client,
    clear_soap_cache,
    get_cache_stats
)
from ffiec_data_connect import WebserviceCredentials, FFIECConnection


class TestSOAPClientCache:
    """Test SOAP client caching functionality."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_soap_cache()
    
    def teardown_method(self):
        """Clear cache after each test."""
        clear_soap_cache()
    
    def test_config_creation(self):
        """Test SOAPClientConfig creation from credentials and session."""
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
            creds = WebserviceCredentials()
            session = FFIECConnection()
            
            config = SOAPClientConfig.from_credentials_and_session(creds, session)
            
            assert config.username == 'testuser'
            assert config.password_hash is not None
            assert len(config.password_hash) == 64  # SHA256 hash length
            assert config.wsdl_url is not None
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently."""
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
            creds = WebserviceCredentials()
            session = FFIECConnection()
            
            config1 = SOAPClientConfig.from_credentials_and_session(creds, session)
            config2 = SOAPClientConfig.from_credentials_and_session(creds, session)
            
            # Same configuration should produce same cache key
            assert config1.cache_key() == config2.cache_key()
    
    def test_cache_key_different_for_different_credentials(self):
        """Test that different credentials produce different cache keys."""
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'user1', 'FFIEC_PASSWORD': 'pass1'}):
            creds1 = WebserviceCredentials()
            session = FFIECConnection()
            config1 = SOAPClientConfig.from_credentials_and_session(creds1, session)
        
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'user2', 'FFIEC_PASSWORD': 'pass2'}):
            creds2 = WebserviceCredentials()
            config2 = SOAPClientConfig.from_credentials_and_session(creds2, session)
            
            # Different credentials should produce different cache keys
            assert config1.cache_key() != config2.cache_key()
    
    @patch('ffiec_data_connect.soap_cache.Transport')
    @patch('ffiec_data_connect.soap_cache.Client')
    def test_client_caching(self, mock_client_class, mock_transport_class):
        """Test that SOAP clients are cached and reused."""
        mock_client = Mock()
        mock_transport = Mock()
        mock_client_class.return_value = mock_client
        mock_transport_class.return_value = mock_transport
        
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
            creds = WebserviceCredentials()
            session = Mock()
            
            # First call should create client
            client1 = get_soap_client(creds, session)
            assert client1 == mock_client
            assert mock_client_class.call_count == 1
            
            # Second call should return cached client
            client2 = get_soap_client(creds, session)
            assert client2 == mock_client
            assert client1 is client2
            # Should not have created a new client
            assert mock_client_class.call_count == 1
    
    @patch('ffiec_data_connect.soap_cache.Transport')
    @patch('ffiec_data_connect.soap_cache.Client')
    def test_cache_stats(self, mock_client_class, mock_transport_class):
        """Test cache statistics reporting."""
        mock_client_class.return_value = Mock()
        mock_transport_class.return_value = Mock()
        
        # Initial stats
        stats = get_cache_stats()
        assert stats['size'] == 0
        
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
            creds = WebserviceCredentials()
            session = Mock()
            session.headers = {}
            
            # Add client to cache
            get_soap_client(creds, session)
            
            # Check updated stats
            stats = get_cache_stats()
            assert stats['size'] == 1
            assert stats['max_size'] > 0
    
    @patch('ffiec_data_connect.soap_cache.Transport')
    @patch('ffiec_data_connect.soap_cache.Client')
    def test_cache_clearing(self, mock_client_class, mock_transport_class):
        """Test cache clearing functionality."""
        mock_client_class.return_value = Mock()
        mock_transport_class.return_value = Mock()
        
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
            creds = WebserviceCredentials()
            session = Mock()
            session.headers = {}
            
            # Add client to cache
            get_soap_client(creds, session)
            assert get_cache_stats()['size'] == 1
            
            # Clear cache
            clear_soap_cache()
            assert get_cache_stats()['size'] == 0
            
            # Next call should create new client
            get_soap_client(creds, session)
            assert mock_client_class.call_count == 2
    
    def test_cache_lru_eviction(self):
        """Test that LRU eviction works correctly."""
        cache = SOAPClientCache(max_size=2)
        
        # Mock clients
        client1, client2, client3 = Mock(), Mock(), Mock()
        
        with patch('ffiec_data_connect.soap_cache.Client', side_effect=[client1, client2, client3]):
            with patch.dict('os.environ', {'FFIEC_USERNAME': 'user1', 'FFIEC_PASSWORD': 'pass1'}):
                creds1 = WebserviceCredentials()
                session = Mock()
                session.headers = {}
                config1 = SOAPClientConfig.from_credentials_and_session(creds1, session)
                
            with patch.dict('os.environ', {'FFIEC_USERNAME': 'user2', 'FFIEC_PASSWORD': 'pass2'}):
                creds2 = WebserviceCredentials()
                config2 = SOAPClientConfig.from_credentials_and_session(creds2, session)
                
            with patch.dict('os.environ', {'FFIEC_USERNAME': 'user3', 'FFIEC_PASSWORD': 'pass3'}):
                creds3 = WebserviceCredentials()
                config3 = SOAPClientConfig.from_credentials_and_session(creds3, session)
            
            # Add first two clients (cache at max size)
            c1 = cache.get_client(config1, creds1, session)
            c2 = cache.get_client(config2, creds2, session)
            
            assert len(cache._cache) == 2
            
            # Add third client - should evict first (LRU)
            c3 = cache.get_client(config3, creds3, session)
            
            assert len(cache._cache) == 2
            # First client should be evicted
            assert config1.cache_key() not in cache._cache
            assert config2.cache_key() in cache._cache
            assert config3.cache_key() in cache._cache


class TestCredentialImmutability:
    """Test credential immutability for race condition prevention."""
    
    def test_credentials_immutable_after_init(self):
        """Test that credentials cannot be modified after initialization."""
        with patch.dict('os.environ', {'FFIEC_USERNAME': 'testuser', 'FFIEC_PASSWORD': 'testpass'}):
            creds = WebserviceCredentials()
            
            # Should not be able to modify username
            with pytest.raises(Exception) as exc_info:
                creds.username = 'newuser'
            
            # Should not be able to modify password  
            with pytest.raises(Exception) as exc_info:
                creds.password = 'newpass'
            
            # Original values should be unchanged
            assert creds.username == 'testuser'
            assert creds.password == 'testpass'
    
    def test_credentials_can_be_set_during_init(self):
        """Test that credentials can still be set via constructor."""
        creds = WebserviceCredentials('myuser', 'mypass')
        
        assert creds.username == 'myuser'
        assert creds.password == 'mypass'
        
        # But should not be modifiable after
        with pytest.raises(Exception):
            creds.username = 'newuser'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])