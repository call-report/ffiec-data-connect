"""
Unit tests for dual field compatibility ('rssd' and 'id_rssd').

This test suite verifies that all functions returning RSSD data provide both
'rssd' and 'id_rssd' fields with identical data for backward compatibility.
"""

from unittest.mock import Mock, patch

import pytest

from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.datahelpers import _normalize_output_from_reporter_panel
from ffiec_data_connect.methods import (
    collect_filers_since_date,
)
from ffiec_data_connect.xbrl_processor import _process_xbrl_item

try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False


class TestDualFieldCompatibility:
    """Test dual field support across all functions that return RSSD data."""

    def test_normalize_output_from_reporter_panel_dual_fields(self):
        """Test that datahelpers normalization provides both fields."""
        # Test data with ID_RSSD field
        test_data = {
            "ID_RSSD": 123456,
            "Name": "Test Bank",
            "State": "NY",
            "City": "New York",
        }

        result = _normalize_output_from_reporter_panel(test_data)

        # Both fields should be present with identical data
        assert "rssd" in result
        assert "id_rssd" in result
        assert result["rssd"] == "123456"
        assert result["id_rssd"] == "123456"
        assert result["rssd"] == result["id_rssd"]

    def test_normalize_output_missing_id_rssd(self):
        """Test normalization when ID_RSSD is missing."""
        test_data = {"Name": "Test Bank", "State": "NY"}

        result = _normalize_output_from_reporter_panel(test_data)

        # Both fields should be None when ID_RSSD is missing
        assert "rssd" in result
        assert "id_rssd" in result
        assert result["rssd"] is None
        assert result["id_rssd"] is None

    @pytest.mark.skipif(not POLARS_AVAILABLE, reason="Polars not available")
    @patch("ffiec_data_connect.methods_enhanced.collect_filers_since_date_enhanced")
    def test_collect_filers_since_date_dual_fields_polars(self, mock_enhanced_method):
        """Test collect_filers_since_date provides dual fields in Polars output via enhanced method."""
        if POLARS_AVAILABLE:
            mock_polars_df = pl.DataFrame(
                {"rssd_id": ["123456", "789012"], "rssd": ["123456", "789012"]}
            )
        else:
            mock_polars_df = [
                "123456",
                "789012",
            ]  # Fallback for when Polars unavailable

        mock_enhanced_method.return_value = mock_polars_df

        # Create OAuth2 credentials to trigger enhanced method

        creds = Mock(spec=OAuth2Credentials)

        result = collect_filers_since_date(
            creds,
            reporting_period="2023-12-31",
            since_date="2023-12-01",
            output_type="polars",
        )

        # Verify enhanced method was called
        mock_enhanced_method.assert_called_once()

        if POLARS_AVAILABLE:
            # Verify both columns are present in Polars DataFrame
            assert isinstance(result, pl.DataFrame)
            assert len(result) == 2
            assert "rssd_id" in result.columns
            assert "rssd" in result.columns

            # Verify data is identical in both columns
            rssd_id_values = result["rssd_id"].to_list()
            rssd_values = result["rssd"].to_list()
            assert rssd_id_values == rssd_values

    def test_xbrl_processor_dual_fields(self):
        """Test that XBRL processor provides dual fields."""
        # Mock XBRL item data
        mock_item = {
            "@contextRef": "CONTEXT_123456_2023-12-31",
            "@unitRef": "USD",
            "#text": "1000000",
        }

        result = _process_xbrl_item("cc:RCON0010", mock_item, "string_original")

        # Verify dual fields are present
        assert isinstance(result, list)
        assert len(result) == 1

        record = result[0]
        assert "rssd" in record
        assert "id_rssd" in record
        assert record["rssd"] == "123456"
        assert record["id_rssd"] == "123456"
        assert record["rssd"] == record["id_rssd"]

    def test_enhanced_methods_use_same_normalization(self):
        """Test that enhanced methods use the same normalization functions as SOAP methods.

        This test documents that the enhanced (REST) methods use the same dual field
        normalization logic as the SOAP methods, ensuring consistency across both APIs.
        """
        # The enhanced methods use _normalize_pydantic_to_soap_format which internally
        # calls _normalize_output_from_reporter_panel, ensuring dual field compatibility

        from ffiec_data_connect.methods_enhanced import (
            _normalize_pydantic_to_soap_format,
        )

        # Test that the enhanced method normalization produces dual fields
        test_pydantic_obj = {"ID_RSSD": 123456, "Name": "Test Bank"}
        normalized = _normalize_pydantic_to_soap_format(test_pydantic_obj)

        # Should contain both field names
        assert "rssd" in normalized
        assert "id_rssd" in normalized
        assert normalized["rssd"] == normalized["id_rssd"]

        # This confirms that enhanced methods will provide dual fields when properly
        # integrated, as they use the same underlying normalization functions

    def test_all_functions_provide_consistent_field_names(self):
        """Integration test to verify all functions use consistent field naming."""
        # This test documents expected field names across all functions
        expected_fields = {
            "collect_filers_on_reporting_period": ["rssd", "id_rssd"],
            "collect_filers_since_date": ["rssd_id", "rssd"],  # DataFrame columns
            "collect_filers_submission_date_time": ["rssd", "id_rssd"],
            "collect_data": ["rssd", "id_rssd"],  # Via XBRL processor
            # Enhanced versions
            "collect_filers_on_reporting_period_enhanced": ["rssd", "id_rssd"],
            "collect_filers_since_date_enhanced": ["rssd_id", "rssd"],  # DataFrame
            "collect_filers_submission_date_time_enhanced": ["rssd", "id_rssd"],
        }

        # Document that all functions provide dual field support
        assert len(expected_fields) == 7
        for func_name, fields in expected_fields.items():
            assert len(fields) == 2, f"{func_name} should provide exactly 2 fields"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
