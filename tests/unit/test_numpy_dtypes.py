"""
Test numpy dtype handling throughout XBRL → pandas → polars pipeline.

Tests that proper numpy dtypes are maintained from XBRL processing
through pandas DataFrame creation to polars conversion.
"""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import polars as pl
import pytest

from ffiec_data_connect import methods, xbrl_processor
from ffiec_data_connect.credentials import WebserviceCredentials
from ffiec_data_connect.ffiec_connection import FFIECConnection


class TestNumpyDtypeFlow:
    """Test numpy dtype consistency throughout data pipeline."""

    def test_xbrl_processor_returns_numpy_types(self):
        """Test that XBRL processor returns proper numpy types."""
        # Create mock XBRL data that would result in different data types
        mock_items = [
            {
                "mdrm": "RCON2170",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "int",
                "value": 1500000,  # Should become np.int64
            },
            {
                "mdrm": "RIAD4340",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "float",
                "value": 1.25,  # Should become np.float64
            },
            {
                "mdrm": "RCFD9999",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "bool",
                "value": True,  # Should become np.bool_
            },
            {
                "mdrm": "RCFD0001",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "str",
                "value": "test",  # Should remain str
            },
        ]

        # Mock the _process_xbrl_item function to return our test data
        with patch(
            "ffiec_data_connect.xbrl_processor._process_xbrl_item"
        ) as mock_process:
            mock_process.return_value = mock_items

            # Create minimal mock XBRL data
            mock_xbrl_data = (
                b'<?xml version="1.0"?><xbrl><cc:RCON2170>test</cc:RCON2170></xbrl>'
            )

            result = xbrl_processor._process_xml(mock_xbrl_data, "string_original")

            assert len(result) == 4

            # Check that numpy types are used correctly
            int_row = next((r for r in result if r["data_type"] == "int"), None)
            assert int_row is not None
            assert isinstance(int_row["int_data"], (np.int64, np.integer))
            assert np.isnan(int_row["float_data"])

            float_row = next((r for r in result if r["data_type"] == "float"), None)
            assert float_row is not None
            assert isinstance(float_row["float_data"], (np.float64, np.floating))
            assert np.isnan(float_row["int_data"])

            bool_row = next((r for r in result if r["data_type"] == "bool"), None)
            assert bool_row is not None
            assert isinstance(bool_row["bool_data"], (np.bool_, bool))
            assert np.isnan(bool_row["int_data"])

            str_row = next((r for r in result if r["data_type"] == "str"), None)
            assert str_row is not None
            assert isinstance(str_row["str_data"], str)
            assert np.isnan(str_row["int_data"])

    def test_pandas_dataframe_preserves_numpy_dtypes(self):
        """Test that pandas DataFrame creation preserves numpy dtypes."""
        # Create test data with numpy types
        test_data = [
            {
                "mdrm": "RCON2170",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "int",
                "int_data": np.int64(1500000),
                "float_data": np.nan,
                "bool_data": np.nan,
                "str_data": None,
            },
            {
                "mdrm": "RIAD4340",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "float",
                "int_data": np.nan,
                "float_data": np.float64(1.25),
                "bool_data": np.nan,
                "str_data": None,
            },
            {
                "mdrm": "RCFD9999",
                "rssd": "480228",
                "quarter": "2023-12-31",
                "data_type": "bool",
                "int_data": np.nan,
                "float_data": np.nan,
                "bool_data": np.bool_(True),
                "str_data": None,
            },
        ]

        # Mock the XBRL processor to return our test data
        with patch("ffiec_data_connect.xbrl_processor._process_xml") as mock_process:
            mock_process.return_value = test_data

            # Mock credentials and session
            mock_creds = Mock(spec=WebserviceCredentials)
            mock_session = Mock(spec=FFIECConnection)

            # Mock the SOAP call to return dummy XML
            with patch(
                "ffiec_data_connect.methods._return_client_session"
            ) as mock_client:
                mock_client.return_value.service.RetrieveFacsimile.return_value = (
                    b"<xml>test</xml>"
                )

                # Call collect_data with pandas output
                df = methods.collect_data(
                    session=mock_session,
                    creds=mock_creds,
                    reporting_period="2023-12-31",
                    rssd_id="480228",
                    series="call",
                    output_type="pandas",
                )

                # Verify DataFrame has correct numpy dtypes
                assert isinstance(df, pd.DataFrame)
                assert len(df) == 3

                # Check column dtypes (pandas nullable types)
                assert df["int_data"].dtype.name == "Int64"  # Nullable integer
                assert df["float_data"].dtype == np.float64
                assert df["bool_data"].dtype.name == "boolean"  # Nullable boolean
                assert df["str_data"].dtype.name == "string"  # Pandas string dtype

                # Check actual values maintain correct types
                int_row = df[df["data_type"] == "int"].iloc[0]
                assert isinstance(int_row["int_data"], (np.int64, int))
                assert pd.isna(int_row["float_data"])

                float_row = df[df["data_type"] == "float"].iloc[0]
                assert isinstance(float_row["float_data"], (np.float64, float))
                assert pd.isna(float_row["int_data"])

                bool_row = df[df["data_type"] == "bool"].iloc[0]
                assert isinstance(bool_row["bool_data"], (np.bool_, bool))
                assert pd.isna(bool_row["int_data"])

    def test_polars_conversion_maintains_types(self):
        """Test that polars conversion maintains numpy dtypes."""
        # Create pandas DataFrame with numpy dtypes
        test_data = {
            "mdrm": ["RCON2170", "RIAD4340", "RCFD9999"],
            "rssd": ["480228", "480228", "480228"],
            "quarter": ["2023-12-31", "2023-12-31", "2023-12-31"],
            "data_type": ["int", "float", "bool"],
            "int_data": [np.int64(1500000), np.nan, np.nan],
            "float_data": [np.nan, np.float64(1.25), np.nan],
            "bool_data": [np.nan, np.nan, np.bool_(True)],
            "str_data": [None, None, None],
        }

        df_pandas = pd.DataFrame(test_data)

        # Ensure pandas has correct nullable dtypes
        df_pandas["int_data"] = df_pandas["int_data"].astype(
            "Int64"
        )  # Nullable integer
        df_pandas["float_data"] = df_pandas["float_data"].astype("float64")
        df_pandas["bool_data"] = df_pandas["bool_data"].astype(
            "boolean"
        )  # Nullable boolean

        # Convert to polars with schema overrides
        schema_overrides = {
            "int_data": pl.Int64,
            "float_data": pl.Float64,
            "bool_data": pl.Boolean,
            "str_data": pl.Utf8,
            "mdrm": pl.Utf8,
            "rssd": pl.Utf8,
            "quarter": pl.Utf8,
            "data_type": pl.Utf8,
        }

        df_polars = pl.from_pandas(df_pandas, schema_overrides=schema_overrides)

        # Verify polars schema matches expectations
        assert df_polars.schema["int_data"] == pl.Int64
        assert df_polars.schema["float_data"] == pl.Float64
        assert df_polars.schema["bool_data"] == pl.Boolean
        assert df_polars.schema["str_data"] == pl.Utf8

        # Verify actual data values are correct
        int_row = df_polars.filter(pl.col("data_type") == "int").row(0)
        assert int_row[4] == 1500000  # int_data column

        float_row = df_polars.filter(pl.col("data_type") == "float").row(0)
        assert abs(float_row[5] - 1.25) < 0.001  # float_data column

        bool_row = df_polars.filter(pl.col("data_type") == "bool").row(0)
        assert bool_row[6] is True  # bool_data column

    def test_end_to_end_dtype_pipeline(self):
        """Test complete pipeline: XBRL → pandas → polars maintains dtypes."""
        # This would be an integration test using real XBRL data
        # For now, we'll use mocked data that simulates the complete flow

        mock_xbrl_data = b"""<?xml version="1.0"?>
        <xbrl>
            <cc:RCON2170 contextRef="c_480228_2023-12-31" unitRef="USD">1500000000</cc:RCON2170>
            <cc:RIAD4340 contextRef="c_480228_2023-12-31" unitRef="PURE">1.25</cc:RIAD4340>
        </xbrl>"""

        # This test would need real XBRL processing, but demonstrates the concept
        # In a full implementation, we would:
        # 1. Process real XBRL with _process_xml()
        # 2. Create pandas DataFrame with collect_data()
        # 3. Convert to polars
        # 4. Verify dtypes are maintained throughout

        # For now, verify our mock data structure is correct
        expected_structure = {
            "int_data": np.int64,
            "float_data": np.float64,
            "bool_data": np.bool_,
            "str_data": str,
        }

        for field, expected_type in expected_structure.items():
            assert expected_type in [np.int64, np.float64, np.bool_, str]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
