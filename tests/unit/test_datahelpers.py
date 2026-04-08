"""Tests for ffiec_data_connect.datahelpers._normalize_output_from_reporter_panel"""

import pytest
from ffiec_data_connect.datahelpers import _normalize_output_from_reporter_panel


class TestIDRSSD:
    def test_id_rssd_present(self):
        row = {"ID_RSSD": 12345}
        result = _normalize_output_from_reporter_panel(row)
        assert result["id_rssd"] == "12345"
        assert result["rssd"] == "12345"

    def test_id_rssd_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["id_rssd"] is None
        assert result["rssd"] is None


class TestFDICCertNumber:
    def test_nonzero(self):
        row = {"FDICCertNumber": 99887}
        result = _normalize_output_from_reporter_panel(row)
        assert result["fdic_cert_number"] == "99887"

    def test_zero(self):
        row = {"FDICCertNumber": 0}
        result = _normalize_output_from_reporter_panel(row)
        assert result["fdic_cert_number"] is None

    def test_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["fdic_cert_number"] is None


class TestOCCChartNumber:
    def test_nonzero(self):
        row = {"OCCChartNumber": 5432}
        result = _normalize_output_from_reporter_panel(row)
        assert result["occ_chart_number"] == "5432"

    def test_zero(self):
        row = {"OCCChartNumber": 0}
        result = _normalize_output_from_reporter_panel(row)
        assert result["occ_chart_number"] is None

    def test_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["occ_chart_number"] is None


class TestOTSDockNumber:
    def test_nonzero(self):
        row = {"OTSDockNumber": 7777}
        result = _normalize_output_from_reporter_panel(row)
        assert result["ots_dock_number"] == "7777"

    def test_zero(self):
        row = {"OTSDockNumber": 0}
        result = _normalize_output_from_reporter_panel(row)
        assert result["ots_dock_number"] is None

    def test_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["ots_dock_number"] is None


class TestPrimaryABARoutNumber:
    def test_nonzero(self):
        row = {"PrimaryABARoutNumber": 123456789}
        result = _normalize_output_from_reporter_panel(row)
        assert result["primary_aba_rout_number"] == "123456789"

    def test_zero(self):
        row = {"PrimaryABARoutNumber": 0}
        result = _normalize_output_from_reporter_panel(row)
        assert result.get("primary_aba_rout_number") is None


class TestName:
    def test_present_with_value(self):
        row = {"Name": "First National Bank"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["name"] == "First National Bank"

    def test_present_with_zero_string(self):
        row = {"Name": "0"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["name"] == "0"

    def test_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["name"] is None


class TestState:
    def test_present(self):
        row = {"State": "NY"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["state"] == "NY"

    def test_missing_sets_state_to_none(self):
        """When State is missing, state should be set to None."""
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["state"] is None


class TestCity:
    def test_present(self):
        row = {"City": "Albany", "State": "NY"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["city"] == "Albany"

    def test_missing(self):
        row = {"State": "NY"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["city"] is None


class TestAddress:
    def test_present(self):
        row = {"Address": "123 Main St"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["address"] == "123 Main St"


class TestZip:
    def test_integer_zip_padded_to_five(self):
        row = {"Zip": 1234}
        result = _normalize_output_from_reporter_panel(row)
        assert result["zip"] == "01234"

    def test_string_zip(self):
        row = {"Zip": "90210"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["zip"] == "90210"

    def test_uppercase_ZIP(self):
        row = {"ZIP": 501}
        result = _normalize_output_from_reporter_panel(row)
        assert result["zip"] == "00501"

    def test_zip_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert result["zip"] is None

    def test_zip_preferred_over_ZIP(self):
        """When both 'Zip' and 'ZIP' are present, 'Zip' takes precedence."""
        row = {"Zip": 10001, "ZIP": 99999}
        result = _normalize_output_from_reporter_panel(row)
        assert result["zip"] == "10001"


class TestFilingType:
    def test_present_with_value(self):
        row = {"FilingType": "041"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["filing_type"] == "041"


class TestHasFiledForReportingPeriod:
    def test_bool_true(self):
        row = {"HasFiledForReportingPeriod": True}
        result = _normalize_output_from_reporter_panel(row)
        assert result["has_filed_for_reporting_period"] is True

    def test_bool_false(self):
        row = {"HasFiledForReportingPeriod": False}
        result = _normalize_output_from_reporter_panel(row)
        assert result["has_filed_for_reporting_period"] is False

    def test_non_bool_becomes_none(self):
        row = {"HasFiledForReportingPeriod": "yes"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["has_filed_for_reporting_period"] is None

    def test_missing(self):
        row = {}
        result = _normalize_output_from_reporter_panel(row)
        assert "has_filed_for_reporting_period" not in result


class TestStateZeroString:
    """Test State field with value '0' (line 81)."""

    def test_state_zero_string(self):
        row = {"State": "0"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["state"] == "0"


class TestCityZeroString:
    """Test City field with value '0' (line 91)."""

    def test_city_zero_string(self):
        row = {"City": "0"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["city"] == "0"


class TestAddressZeroString:
    """Test Address field with value '0' (line 101)."""

    def test_address_zero_string(self):
        row = {"Address": "0"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["address"] == "0"


class TestZipZeroValue:
    """Test Zip field with value 0 (line 117: zfill produces '00000', not '0')."""

    def test_zip_integer_zero(self):
        """Zip=0 -> str(0).zfill(5) -> '00000', which is NOT '0', so hits else branch."""
        row = {"Zip": 0}
        result = _normalize_output_from_reporter_panel(row)
        assert result["zip"] == "00000"


class TestFilingTypeZeroString:
    """Test FilingType field with value '0' (line 127)."""

    def test_filing_type_zero_string(self):
        row = {"FilingType": "0"}
        result = _normalize_output_from_reporter_panel(row)
        assert result["filing_type"] == "0"


class TestFieldsEmptyString:
    """Test fields with empty string values to cover the 'or temp_str == ""' branches."""

    def test_state_empty_string(self):
        row = {"State": ""}
        result = _normalize_output_from_reporter_panel(row)
        assert result["state"] == ""

    def test_city_empty_string(self):
        row = {"City": ""}
        result = _normalize_output_from_reporter_panel(row)
        assert result["city"] == ""

    def test_address_empty_string(self):
        row = {"Address": ""}
        result = _normalize_output_from_reporter_panel(row)
        assert result["address"] == ""

    def test_filing_type_empty_string(self):
        row = {"FilingType": ""}
        result = _normalize_output_from_reporter_panel(row)
        assert result["filing_type"] == ""


class TestFullRow:
    """Integration-style test: pass a complete row resembling a REST API response."""

    def test_complete_row(self):
        row = {
            "ID_RSSD": 480228,
            "FDICCertNumber": 12345,
            "OCCChartNumber": 0,
            "OTSDockNumber": 0,
            "PrimaryABARoutNumber": 111000025,
            "Name": "Example Bank",
            "State": "TX",
            "City": "Dallas",
            "Address": "100 Commerce St",
            "Zip": 75201,
            "FilingType": "041",
            "HasFiledForReportingPeriod": True,
        }
        result = _normalize_output_from_reporter_panel(row)

        assert result["id_rssd"] == "480228"
        assert result["rssd"] == "480228"
        assert result["fdic_cert_number"] == "12345"
        assert result["occ_chart_number"] is None
        assert result["ots_dock_number"] is None
        assert result["primary_aba_rout_number"] == "111000025"
        assert result["name"] == "Example Bank"
        assert result["state"] == "TX"
        assert result["city"] == "Dallas"
        assert result["address"] == "100 Commerce St"
        assert result["zip"] == "75201"
        assert result["filing_type"] == "041"
        assert result["has_filed_for_reporting_period"] is True
