"""
Test direct XBRL to polars conversion to ensure maximum type precision.

Tests that direct conversion from XBRL to polars DataFrames preserves
data types and precision without intermediate pandas conversion.
"""

import pytest
import numpy as np
import polars as pl
from unittest.mock import Mock, patch

from ffiec_data_connect import methods
from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.ffiec_connection import FFIECConnection
from ffiec_data_connect.exceptions import ValidationError


class TestPolarsDirectConversion:
    """Test direct XBRL → polars conversion functionality."""
    
    def test_polars_output_type_validation(self):
        """Test that polars is accepted as a valid output type."""
        # Should not raise an exception
        methods._output_type_validator("polars")
        
        # Should raise for invalid types (legacy mode raises ValueError)
        with pytest.raises(ValueError):
            methods._output_type_validator("invalid")
    
    def test_polars_unavailable_error(self):
        """Test proper error when polars is not available."""
        mock_creds = Mock(spec=WebserviceCredentials)
        mock_session = Mock(spec=FFIECConnection)
        
        # Mock polars as unavailable
        with patch('ffiec_data_connect.methods.POLARS_AVAILABLE', False):
            with patch('ffiec_data_connect.methods._return_client_session') as mock_client:
                mock_client.return_value.service.RetrieveFacsimile.return_value = b'<xml>test</xml>'
                
                with patch('ffiec_data_connect.methods.xbrl_processor._process_xml') as mock_process:
                    mock_process.return_value = []
                    
                    with pytest.raises(ValueError) as exc_info:
                        methods.collect_data(
                            session=mock_session,
                            creds=mock_creds,
                            reporting_period='2023-12-31',
                            rssd_id='480228',
                            series='call',
                            output_type='polars'
                        )
                    
                    assert "Polars not available" in str(exc_info.value)
    
    def test_direct_polars_conversion_preserves_types(self):
        """Test that direct polars conversion preserves data types."""
        # Mock test data with different types
        test_data = [
            {
                'mdrm': 'RCON2170',
                'rssd': '480228',
                'quarter': '2023-12-31',
                'data_type': 'int',
                'int_data': np.int64(1500000),
                'float_data': np.nan,
                'bool_data': np.nan,
                'str_data': None
            },
            {
                'mdrm': 'RIAD4340', 
                'rssd': '480228',
                'quarter': '2023-12-31',
                'data_type': 'float',
                'int_data': np.nan,
                'float_data': np.float64(1.25),
                'bool_data': np.nan,
                'str_data': None
            },
            {
                'mdrm': 'RCFD9999',
                'rssd': '480228',
                'quarter': '2023-12-31',
                'data_type': 'bool',
                'int_data': np.nan,
                'float_data': np.nan,
                'bool_data': np.bool_(True),
                'str_data': None
            },
            {
                'mdrm': 'RCFD0001',
                'rssd': '480228',
                'quarter': '2023-12-31',
                'data_type': 'str',
                'int_data': np.nan,
                'float_data': np.nan,
                'bool_data': np.nan,
                'str_data': 'test'
            }
        ]
        
        mock_creds = Mock(spec=WebserviceCredentials)
        mock_session = Mock(spec=FFIECConnection)
        
        with patch('ffiec_data_connect.methods.POLARS_AVAILABLE', True):
            with patch('ffiec_data_connect.methods._return_client_session') as mock_client:
                mock_client.return_value.service.RetrieveFacsimile.return_value = b'<xml>test</xml>'
                
                with patch('ffiec_data_connect.methods.xbrl_processor._process_xml') as mock_process:
                    mock_process.return_value = test_data
                    
                    # Get direct polars conversion
                    df_polars = methods.collect_data(
                        session=mock_session,
                        creds=mock_creds,
                        reporting_period='2023-12-31',
                        rssd_id='480228',
                        series='call',
                        output_type='polars'
                    )
                    
                    # Verify it's a polars DataFrame
                    assert isinstance(df_polars, pl.DataFrame)
                    assert df_polars.height == 4
                    
                    # Verify schema has correct types
                    expected_schema = {
                        'mdrm': pl.Utf8,
                        'rssd': pl.Utf8,
                        'quarter': pl.Utf8,
                        'data_type': pl.Utf8,
                        'int_data': pl.Int64,
                        'float_data': pl.Float64,
                        'bool_data': pl.Boolean,
                        'str_data': pl.Utf8
                    }
                    
                    for col, expected_type in expected_schema.items():
                        assert df_polars.schema[col] == expected_type
                    
                    # Verify actual values are correct and properly typed
                    int_row = df_polars.filter(pl.col('data_type') == 'int').row(0)
                    assert int_row[4] == 1500000  # int_data column
                    
                    float_row = df_polars.filter(pl.col('data_type') == 'float').row(0)
                    assert abs(float_row[5] - 1.25) < 0.001  # float_data column
                    
                    bool_row = df_polars.filter(pl.col('data_type') == 'bool').row(0)
                    assert bool_row[6] is True  # bool_data column
                    
                    str_row = df_polars.filter(pl.col('data_type') == 'str').row(0)
                    assert str_row[7] == 'test'  # str_data column
    
    def test_empty_data_returns_correct_schema(self):
        """Test that empty data returns polars DataFrame with correct schema."""
        mock_creds = Mock(spec=WebserviceCredentials)
        mock_session = Mock(spec=FFIECConnection)
        
        with patch('ffiec_data_connect.methods.POLARS_AVAILABLE', True):
            with patch('ffiec_data_connect.methods._return_client_session') as mock_client:
                mock_client.return_value.service.RetrieveFacsimile.return_value = b'<xml>test</xml>'
                
                with patch('ffiec_data_connect.methods.xbrl_processor._process_xml') as mock_process:
                    mock_process.return_value = []  # Empty data
                    
                    df_polars = methods.collect_data(
                        session=mock_session,
                        creds=mock_creds,
                        reporting_period='2023-12-31',
                        rssd_id='480228',
                        series='call',
                        output_type='polars'
                    )
                    
                    # Verify empty DataFrame with correct schema
                    assert isinstance(df_polars, pl.DataFrame)
                    assert df_polars.height == 0
                    
                    expected_schema = {
                        'mdrm': pl.Utf8,
                        'rssd': pl.Utf8,
                        'quarter': pl.Utf8,
                        'data_type': pl.Utf8,
                        'int_data': pl.Int64,
                        'float_data': pl.Float64,
                        'bool_data': pl.Boolean,
                        'str_data': pl.Utf8
                    }
                    
                    for col, expected_type in expected_schema.items():
                        assert df_polars.schema[col] == expected_type
    
    def test_numpy_nan_handling_in_polars(self):
        """Test that numpy NaN values are properly converted to polars nulls."""
        test_data = [
            {
                'mdrm': 'TEST001',
                'rssd': '123456',
                'quarter': '2023-12-31',
                'data_type': 'int',
                'int_data': np.int64(1000),
                'float_data': np.nan,  # Should become null
                'bool_data': np.nan,   # Should become null
                'str_data': None       # Should become null
            }
        ]
        
        mock_creds = Mock(spec=WebserviceCredentials)
        mock_session = Mock(spec=FFIECConnection)
        
        with patch('ffiec_data_connect.methods.POLARS_AVAILABLE', True):
            with patch('ffiec_data_connect.methods._return_client_session') as mock_client:
                mock_client.return_value.service.RetrieveFacsimile.return_value = b'<xml>test</xml>'
                
                with patch('ffiec_data_connect.methods.xbrl_processor._process_xml') as mock_process:
                    mock_process.return_value = test_data
                    
                    df_polars = methods.collect_data(
                        session=mock_session,
                        creds=mock_creds,
                        reporting_period='2023-12-31',
                        rssd_id='123456',
                        series='call',
                        output_type='polars'
                    )
                    
                    # Verify nulls are handled correctly
                    row = df_polars.row(0)
                    assert row[4] == 1000         # int_data is not null
                    assert row[5] is None         # float_data is null
                    assert row[6] is None         # bool_data is null
                    assert row[7] is None         # str_data is null


if __name__ == "__main__":
    pytest.main([__file__, "-v"])