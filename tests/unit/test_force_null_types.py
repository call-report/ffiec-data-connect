"""
Unit tests for force_null_types parameter in collect_data methods.

Tests the ability to override default null handling for SOAP/REST.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from ffiec_data_connect import methods
from ffiec_data_connect.credentials import OAuth2Credentials, WebserviceCredentials


class TestForceNullTypes:
    """Test force_null_types parameter functionality."""

    @patch('ffiec_data_connect.methods._return_client_session')
    @patch('ffiec_data_connect.xbrl_processor._process_xml')
    def test_force_numpy_nulls_with_soap(self, mock_process_xml, mock_client):
        """Test forcing numpy nulls with SOAP credentials."""
        # Setup
        mock_soap_client = MagicMock()
        mock_client.return_value = mock_soap_client
        mock_soap_client.service.RetrieveUBPRFacsimileData.return_value = b"<xbrl>test</xbrl>"
        mock_process_xml.return_value = [
            {"int_data": 100, "float_data": np.nan, "str_data": None}
        ]

        creds = WebserviceCredentials("test", "pass")

        # Call with force_null_types="numpy"
        result = methods.collect_data(
            session=MagicMock(),
            creds=creds,
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call",
            force_null_types="numpy"
        )

        # Verify numpy nulls were forced
        mock_process_xml.assert_called()
        call_args = mock_process_xml.call_args
        assert call_args[1].get('use_rest_nulls') is False

    @patch('ffiec_data_connect.methods._return_client_session')
    @patch('ffiec_data_connect.xbrl_processor._process_xml')
    def test_force_pandas_nulls_with_soap(self, mock_process_xml, mock_client):
        """Test forcing pandas nulls with SOAP credentials."""
        # Setup
        mock_soap_client = MagicMock()
        mock_client.return_value = mock_soap_client
        mock_soap_client.service.RetrieveUBPRFacsimileData.return_value = b"<xbrl>test</xbrl>"
        mock_process_xml.return_value = [
            {"int_data": 100, "float_data": pd.NA, "str_data": None}
        ]

        creds = WebserviceCredentials("test", "pass")

        # Call with force_null_types="pandas"
        result = methods.collect_data(
            session=MagicMock(),
            creds=creds,
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call",
            force_null_types="pandas"
        )

        # Verify pandas nulls were forced
        mock_process_xml.assert_called()
        call_args = mock_process_xml.call_args
        assert call_args[1].get('use_rest_nulls') is True

    def test_invalid_force_null_types_value(self):
        """Test that invalid force_null_types value raises error."""
        creds = WebserviceCredentials("test", "pass")

        with pytest.raises(ValueError) as exc_info:
            methods.collect_data(
                session=MagicMock(),
                creds=creds,
                reporting_period="12/31/2023",
                rssd_id="12345",
                series="call",
                force_null_types="invalid"  # Should only be 'numpy' or 'pandas'
            )

        assert "force_null_types" in str(exc_info.value)
        assert "numpy" in str(exc_info.value)
        assert "pandas" in str(exc_info.value)

    @patch('ffiec_data_connect.methods._return_client_session')
    @patch('ffiec_data_connect.xbrl_processor._process_xml')
    def test_default_null_handling_soap(self, mock_process_xml, mock_client):
        """Test default null handling with SOAP (should use numpy)."""
        # Setup
        mock_soap_client = MagicMock()
        mock_client.return_value = mock_soap_client
        mock_soap_client.service.RetrieveUBPRFacsimileData.return_value = b"<xbrl>test</xbrl>"
        mock_process_xml.return_value = [
            {"int_data": 100, "float_data": np.nan, "str_data": None}
        ]

        creds = WebserviceCredentials("test", "pass")

        # Call without force_null_types (should default to numpy for SOAP)
        result = methods.collect_data(
            session=MagicMock(),
            creds=creds,
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call"
        )

        # Verify numpy nulls were used by default for SOAP
        mock_process_xml.assert_called()
        call_args = mock_process_xml.call_args
        assert call_args[1].get('use_rest_nulls') is False

    @patch('ffiec_data_connect.protocol_adapter.create_protocol_adapter')
    def test_default_null_handling_rest(self, mock_adapter):
        """Test default null handling with REST (should use pandas)."""
        # Setup mock REST adapter
        mock_rest = MagicMock()
        mock_adapter.return_value = mock_rest
        mock_rest.is_rest.return_value = True
        mock_rest.collect_data.return_value = [
            {"int_data": 100, "float_data": pd.NA, "str_data": None}
        ]

        creds = OAuth2Credentials(
            username="test",
            bearer_token="eyJhbGci.",
            token_expires=datetime.now() + timedelta(days=90)
        )

        # Call without force_null_types (should default to pandas for REST)
        result = methods.collect_data(
            session=None,  # REST uses None for session
            creds=creds,
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call"
        )

        # The REST adapter should be called
        mock_adapter.assert_called_with(creds)

    @patch('ffiec_data_connect.methods._return_client_session')
    @patch('ffiec_data_connect.xbrl_processor._process_xml')
    def test_force_null_types_with_pandas_output(self, mock_process_xml, mock_client):
        """Test force_null_types with pandas DataFrame output."""
        # Setup
        mock_soap_client = MagicMock()
        mock_client.return_value = mock_soap_client
        mock_soap_client.service.RetrieveUBPRFacsimileData.return_value = b"<xbrl>test</xbrl>"

        # Return data with integers
        mock_process_xml.return_value = [
            {"mdrm": "TEST1", "int_data": 100, "float_data": np.nan},
            {"mdrm": "TEST2", "int_data": 200, "float_data": np.nan},
        ]

        creds = WebserviceCredentials("test", "pass")

        # Call with pandas output and force_null_types="pandas"
        result = methods.collect_data(
            session=MagicMock(),
            creds=creds,
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call",
            output_type="pandas",
            force_null_types="pandas"
        )

        # Should get pandas DataFrame
        assert isinstance(result, pd.DataFrame)

        # Check that int_data column uses nullable integer type
        if "int_data" in result.columns:
            # When using pandas nulls, integers should stay as integers
            assert result["int_data"].dtype in [pd.Int64Dtype(), "Int64", "int64"]

    @patch('ffiec_data_connect.methods._return_client_session') 
    @patch('ffiec_data_connect.xbrl_processor._process_xml')
    def test_force_null_types_with_polars_output(self, mock_process_xml, mock_client):
        """Test force_null_types doesn't affect Polars output."""
        pytest.importorskip("polars")
        import polars as pl

        # Setup
        mock_soap_client = MagicMock()
        mock_client.return_value = mock_soap_client
        mock_soap_client.service.RetrieveUBPRFacsimileData.return_value = b"<xbrl>test</xbrl>"
        mock_process_xml.return_value = [
            {"mdrm": "TEST1", "int_data": 100, "float_data": None}
        ]

        creds = WebserviceCredentials("test", "pass")

        # Call with polars output
        result = methods.collect_data(
            session=MagicMock(),
            creds=creds,
            reporting_period="12/31/2023",
            rssd_id="12345",
            series="call",
            output_type="polars",
            force_null_types="numpy"  # Should not affect Polars
        )

        # Should get Polars DataFrame
        assert isinstance(result, pl.DataFrame)


class TestForceNullTypesIntegration:
    """Integration tests for force_null_types across different methods."""

    @patch('ffiec_data_connect.methods._return_client_session')
    def test_collect_ubpr_facsimile_with_force_null_types(self, mock_client):
        """Test collect_ubpr_facsimile_data respects force_null_types."""
        mock_soap_client = MagicMock()
        mock_client.return_value = mock_soap_client
        mock_soap_client.service.RetrieveUBPRFacsimileData.return_value = b"<xbrl>test</xbrl>"

        creds = WebserviceCredentials("test", "pass")

        # Should not raise error with valid force_null_types
        methods.collect_ubpr_facsimile_data(
            session=MagicMock(),
            creds=creds,
            rssd_id="12345",
            reporting_period="12/31/2023",
            force_null_types="pandas"
        )

        # Should raise error with invalid force_null_types
        with pytest.raises(ValueError):
            methods.collect_ubpr_facsimile_data(
                session=MagicMock(),
                creds=creds,
                rssd_id="12345",
                reporting_period="12/31/2023",
                force_null_types="invalid"
            )
