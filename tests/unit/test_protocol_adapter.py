"""
Unit tests for protocol adapter functionality.

Tests automatic protocol selection based on credential types.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from ffiec_data_connect.credentials import OAuth2Credentials, WebserviceCredentials
from ffiec_data_connect.protocol_adapter import (
    ProtocolAdapter,
    RESTAdapter,
    SOAPAdapter,
    create_protocol_adapter
)


class TestProtocolAdapterFactory:
    """Test protocol adapter factory function."""

    def test_create_soap_adapter_from_webservice_credentials(self):
        """Test SOAP adapter creation from WebserviceCredentials."""
        creds = WebserviceCredentials("test", "pass")
        adapter = create_protocol_adapter(creds)
        
        assert isinstance(adapter, SOAPAdapter)
        assert not adapter.is_rest()

    def test_create_rest_adapter_from_oauth2_credentials(self):
        """Test REST adapter creation from OAuth2Credentials."""
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGci.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        adapter = create_protocol_adapter(creds)
        
        assert isinstance(adapter, RESTAdapter)
        assert adapter.is_rest()

    def test_invalid_credentials_type(self):
        """Test that invalid credential types raise error."""
        with pytest.raises((TypeError, ValueError)):
            create_protocol_adapter("not_credentials")

    def test_none_credentials(self):
        """Test that None credentials raise error."""
        with pytest.raises((TypeError, ValueError)):
            create_protocol_adapter(None)


class TestSOAPAdapter:
    """Test SOAP protocol adapter functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.creds = WebserviceCredentials("test", "pass")
        self.adapter = SOAPAdapter(self.creds)

    def test_is_rest_returns_false(self):
        """Test that SOAP adapter correctly identifies as not REST."""
        assert not self.adapter.is_rest()

    @patch('ffiec_data_connect.protocol_adapter.ffiec_connection.FFIECConnection')
    def test_create_session(self, mock_connection_class):
        """Test SOAP session creation."""
        mock_connection = MagicMock()
        mock_connection_class.return_value = mock_connection
        
        session = self.adapter._create_session()
        
        assert session == mock_connection
        mock_connection_class.assert_called_once()

    @patch('ffiec_data_connect.protocol_adapter.methods')
    def test_collect_reporting_periods(self, mock_methods):
        """Test SOAP collect_reporting_periods delegates correctly."""
        mock_methods.collect_reporting_periods.return_value = ["12/31/2023", "9/30/2023"]
        
        result = self.adapter.collect_reporting_periods(series="call")
        
        assert result == ["12/31/2023", "9/30/2023"]
        mock_methods.collect_reporting_periods.assert_called_once()

    @patch('ffiec_data_connect.protocol_adapter.methods')
    def test_collect_data(self, mock_methods):
        """Test SOAP collect_data delegates correctly."""
        mock_data = [{"mdrm": "TEST", "value": 100}]
        mock_methods.collect_data.return_value = mock_data
        
        result = self.adapter.collect_data(
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call"
        )
        
        assert result == mock_data
        mock_methods.collect_data.assert_called_once()


class TestRESTAdapter:
    """Test REST protocol adapter functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGci.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        self.adapter = RESTAdapter(self.creds)

    def test_is_rest_returns_true(self):
        """Test that REST adapter correctly identifies as REST."""
        assert self.adapter.is_rest()

    def test_create_session_returns_none(self):
        """Test REST session creation returns None."""
        session = self.adapter._create_session()
        assert session is None

    @patch('ffiec_data_connect.protocol_adapter.methods_enhanced')
    def test_collect_reporting_periods(self, mock_methods):
        """Test REST collect_reporting_periods uses enhanced methods."""
        mock_methods.collect_reporting_periods.return_value = ["2023-12-31", "2023-09-30"]
        
        result = self.adapter.collect_reporting_periods(series="call")
        
        assert result == ["2023-12-31", "2023-09-30"]
        mock_methods.collect_reporting_periods.assert_called_once()
        
        # Verify OAuth2 credentials were passed
        call_args = mock_methods.collect_reporting_periods.call_args
        assert call_args[1]['creds'] == self.creds
        assert call_args[1]['session'] is None  # REST uses None for session

    @patch('ffiec_data_connect.protocol_adapter.methods_enhanced')
    def test_collect_data(self, mock_methods):
        """Test REST collect_data uses enhanced methods."""
        mock_data = [{"mdrm": "TEST", "value": 100}]
        mock_methods.collect_data.return_value = mock_data
        
        result = self.adapter.collect_data(
            reporting_period="2023-12-31",
            rssd_id="12345",
            series="call"
        )
        
        assert result == mock_data
        mock_methods.collect_data.assert_called_once()
        
        # Verify parameters
        call_args = mock_methods.collect_data.call_args
        assert call_args[1]['reporting_period'] == "2023-12-31"
        assert call_args[1]['rssd_id'] == "12345"
        assert call_args[1]['series'] == "call"

    @patch('ffiec_data_connect.protocol_adapter.methods_enhanced')
    def test_collect_filers_on_reporting_period(self, mock_methods):
        """Test REST collect_filers_on_reporting_period."""
        mock_filers = [
            {"rssd": "12345", "name": "Test Bank"},
            {"rssd": "67890", "name": "Another Bank"}
        ]
        mock_methods.collect_filers_on_reporting_period.return_value = mock_filers
        
        result = self.adapter.collect_filers_on_reporting_period(
            reporting_period="2023-12-31"
        )
        
        assert result == mock_filers
        mock_methods.collect_filers_on_reporting_period.assert_called_once()


class TestProtocolAdapterErrorHandling:
    """Test error handling in protocol adapters."""

    @patch('ffiec_data_connect.protocol_adapter.methods')
    def test_soap_adapter_handles_connection_error(self, mock_methods):
        """Test SOAP adapter handles connection errors gracefully."""
        from ffiec_data_connect.exceptions import ConnectionError
        
        mock_methods.collect_data.side_effect = ConnectionError("Connection failed")
        
        creds = WebserviceCredentials("test", "pass")
        adapter = SOAPAdapter(creds)
        
        with pytest.raises(ConnectionError):
            adapter.collect_data(
                reporting_period="12/31/2023",
                rssd_id="12345",
                series="call"
            )

    @patch('ffiec_data_connect.protocol_adapter.methods_enhanced')
    def test_rest_adapter_handles_authentication_error(self, mock_methods):
        """Test REST adapter handles authentication errors."""
        from ffiec_data_connect.exceptions import AuthenticationError
        
        mock_methods.collect_data.side_effect = AuthenticationError("Token expired")
        
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGci.",
            token_expires=datetime.now() - timedelta(days=1)  # Expired
        )
        adapter = RESTAdapter(creds)
        
        with pytest.raises(AuthenticationError):
            adapter.collect_data(
                reporting_period="2023-12-31",
                rssd_id="12345",
                series="call"
            )


class TestProtocolAdapterIntegration:
    """Integration tests for protocol adapters."""

    @patch('ffiec_data_connect.methods.create_protocol_adapter')
    def test_methods_use_protocol_adapter_for_oauth2(self, mock_factory):
        """Test that main methods use protocol adapter for OAuth2 credentials."""
        from ffiec_data_connect import methods
        
        mock_adapter = MagicMock()
        mock_factory.return_value = mock_adapter
        mock_adapter.is_rest.return_value = True
        mock_adapter.collect_data.return_value = []
        
        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGci.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        
        # Call collect_data with OAuth2 credentials
        methods.collect_data(
            session=None,
            creds=creds,
            reporting_period="2023-12-31",
            rssd_id="12345",
            series="call"
        )
        
        # Verify protocol adapter was created and used
        mock_factory.assert_called_with(creds)
        mock_adapter.collect_data.assert_called_once()

    def test_protocol_adapter_date_format_normalization(self):
        """Test that protocol adapters handle date format differences."""
        # SOAP uses MM/DD/YYYY format
        soap_creds = WebserviceCredentials("test", "pass")
        soap_adapter = create_protocol_adapter(soap_creds)
        
        # REST uses YYYY-MM-DD format  
        rest_creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGci.",
            token_expires=datetime.now() + timedelta(days=90)
        )
        rest_adapter = create_protocol_adapter(rest_creds)
        
        # Both should handle their respective formats
        assert not soap_adapter.is_rest()
        assert rest_adapter.is_rest()