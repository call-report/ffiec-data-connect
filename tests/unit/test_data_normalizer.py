"""
Unit tests for DataNormalizer - comprehensive coverage of all static methods.

All methods under test are pure functions operating on data structures,
so no mocking or live API access is required.
"""

import logging
from datetime import datetime

import pytest

from ffiec_data_connect.data_normalizer import DataNormalizer


# ---------------------------------------------------------------------------
# 1. _fix_zip_code
# ---------------------------------------------------------------------------

class TestFixZipCode:
    """Tests for ZIP code leading-zero restoration."""

    @pytest.mark.parametrize("input_zip,expected", [
        (2886, "02886"),       # 4-digit int -> 5-digit with leading zero
        (886, "00886"),        # 3-digit int
        (86, "00086"),         # 2-digit int
        (6, "00006"),          # 1-digit int
        (12345, "12345"),      # already 5 digits
        (99999, "99999"),      # max 5-digit
        (0, "00000"),          # zero
    ])
    def test_integer_inputs(self, input_zip, expected):
        result = DataNormalizer._fix_zip_code(input_zip)
        assert result == expected
        assert isinstance(result, str)

    @pytest.mark.parametrize("input_zip,expected", [
        ("2886", "02886"),     # 4-char string padded
        ("886", "00886"),      # 3-char string padded
        ("02886", "02886"),    # already correct
        ("12345", "12345"),    # already 5 digits
        ("1", "00001"),        # single char
    ])
    def test_string_inputs_needing_padding(self, input_zip, expected):
        result = DataNormalizer._fix_zip_code(input_zip)
        assert result == expected
        assert isinstance(result, str)

    def test_string_with_leading_whitespace(self):
        result = DataNormalizer._fix_zip_code("  2886  ")
        assert result == "02886"

    def test_none_returns_empty(self):
        assert DataNormalizer._fix_zip_code(None) == ""

    def test_empty_string_returns_empty(self):
        assert DataNormalizer._fix_zip_code("") == ""

    def test_non_numeric_string_returned_as_is(self):
        # Non-digit strings are returned stripped but unpadded
        assert DataNormalizer._fix_zip_code("abc") == "abc"

    def test_already_five_digit_string(self):
        assert DataNormalizer._fix_zip_code("02886") == "02886"

    def test_negative_integer(self):
        # Negative number: str(-1) is "-1" (len 2), so the code pads it
        result = DataNormalizer._fix_zip_code(-1)
        assert result == "000-1"
        assert isinstance(result, str)

    def test_non_standard_type_converted_to_str(self):
        # e.g., a float -- falls through to the else branch
        result = DataNormalizer._fix_zip_code(2886.0)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 2. _normalize_datetime
# ---------------------------------------------------------------------------

class TestNormalizeDatetime:
    """Tests for datetime normalization to SOAP format."""

    def test_datetime_object_formatted(self):
        dt = datetime(2023, 12, 31, 23, 59, 59)
        result = DataNormalizer._normalize_datetime(dt)
        # SOAP format uses non-zero-padded month/day/hour
        assert "12/31/2023" in result
        assert isinstance(result, str)

    def test_datetime_object_am_pm(self):
        dt = datetime(2024, 1, 1, 9, 0, 0)
        result = DataNormalizer._normalize_datetime(dt)
        assert "AM" in result or "am" in result.lower()

    def test_string_input_returned_stripped(self):
        result = DataNormalizer._normalize_datetime("  12/31/2023 11:59:59 PM  ")
        assert result == "12/31/2023 11:59:59 PM"

    def test_string_input_already_clean(self):
        result = DataNormalizer._normalize_datetime("1/1/2024 9:00:00 AM")
        assert result == "1/1/2024 9:00:00 AM"

    def test_none_returns_empty_string(self):
        assert DataNormalizer._normalize_datetime(None) == ""

    def test_non_string_non_datetime_converted(self):
        result = DataNormalizer._normalize_datetime(12345)
        assert result == "12345"


# ---------------------------------------------------------------------------
# 3. _normalize_date_string
# ---------------------------------------------------------------------------

class TestNormalizeDateString:
    """Tests for reporting-period date string normalization."""

    @pytest.mark.parametrize("date_str", [
        "12/31/2023",
        "1/1/2024",
        "6/30/2023",
    ])
    def test_valid_mm_dd_yyyy_returned(self, date_str):
        assert DataNormalizer._normalize_date_string(date_str) == date_str

    def test_strips_whitespace(self):
        assert DataNormalizer._normalize_date_string("  3/31/2024  ") == "3/31/2024"

    def test_invalid_format_returned_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            result = DataNormalizer._normalize_date_string("2024-01-01")
        assert result == "2024-01-01"
        assert any("Unexpected date format" in r.message for r in caplog.records)

    def test_none_returns_empty(self):
        assert DataNormalizer._normalize_date_string(None) == ""

    def test_non_string_converted(self):
        result = DataNormalizer._normalize_date_string(20240101)
        assert result == "20240101"


# ---------------------------------------------------------------------------
# 4. normalize_for_validation
# ---------------------------------------------------------------------------

class TestNormalizeForValidation:
    """Tests for the combined normalize + stats entry point."""

    def test_rest_protocol_normalizes(self):
        data = [480228, 852320]
        normalized, stats = DataNormalizer.normalize_for_validation(
            data, "RetrieveFilersSinceDate", "REST"
        )
        assert normalized == ["480228", "852320"]
        assert "transformations_applied" in stats or "transformations" in stats

    def test_soap_protocol_passthrough(self):
        data = ["480228"]
        normalized, stats = DataNormalizer.normalize_for_validation(
            data, "RetrieveFilersSinceDate", "SOAP"
        )
        assert normalized is data
        assert stats["transformations"] == 0
        assert stats["protocol"] == "SOAP"

    def test_empty_data(self):
        normalized, stats = DataNormalizer.normalize_for_validation(
            [], "RetrievePanelOfReporters", "REST"
        )
        assert normalized == []


# ---------------------------------------------------------------------------
# 5. validate_pydantic_compatibility
# ---------------------------------------------------------------------------

class TestValidatePydanticCompatibility:
    """Tests for Pydantic pre-validation checks."""

    def test_panel_missing_id_rssd(self):
        data = [{"Name": "Test Bank"}]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        assert report["compatible"] is False
        assert any("missing ID_RSSD" in w for w in report["warnings"])

    def test_panel_wrong_type_id_rssd(self):
        data = [{"ID_RSSD": 12345, "Name": "Bank"}]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        assert report["compatible"] is False
        assert any("not string" in w for w in report["warnings"])

    def test_panel_bad_zip_4_digits(self):
        data = [{"ID_RSSD": "12345", "Name": "Bank", "ZIP": "2886"}]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        assert any("leading zero" in w for w in report["warnings"])

    def test_panel_valid_data(self):
        data = [{"ID_RSSD": "12345", "Name": "Bank", "ZIP": "02886"}]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        assert report["compatible"] is True
        assert len(report["warnings"]) == 0

    def test_filers_since_date_non_string_items(self):
        data = [480228, 852320]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrieveFilersSinceDate"
        )
        assert report["compatible"] is False
        assert any("not string" in w for w in report["warnings"])

    def test_filers_since_date_valid(self):
        data = ["480228", "852320"]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrieveFilersSinceDate"
        )
        assert report["compatible"] is True

    def test_missing_name_field(self):
        data = [{"ID_RSSD": "123"}]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        assert report["compatible"] is False
        assert any("missing Name" in w for w in report["warnings"])


# ---------------------------------------------------------------------------
# 6. normalize_response
# ---------------------------------------------------------------------------

class TestNormalizeResponse:
    """Tests for the main normalization entry point."""

    def test_panel_of_reporters_full(self):
        rest = [
            {
                "ID_RSSD": 480228,
                "FDICCertNumber": 1039,
                "ZIP": 2886,
                "HasFiledForReportingPeriod": True,
                "InstitutionName": "Test Bank",
                "MailingZIP": 2886,
                "OCCChartNumber": 14240,
                "OTSDockNumber": None,
                "PrimaryABARoutNumber": 21000021,
                "PhysicalStreetAddress": "123 MAIN ST",
                "PhysicalCity": "PROVIDENCE",
                "PhysicalState": "RI",
                "MailingStreetAddress": "PO BOX 1",
                "MailingCity": "PROVIDENCE",
                "MailingState": "RI",
            }
        ]
        result = DataNormalizer.normalize_response(rest, "RetrievePanelOfReporters", "REST")
        item = result[0]

        assert item["ID_RSSD"] == "480228"
        assert isinstance(item["ID_RSSD"], str)
        assert item["ZIP"] == "02886"
        assert item["MailingZIP"] == "02886"
        assert item["HasFiledForReportingPeriod"] == "true"
        assert item["FDICCertNumber"] == "1039"
        assert item["OTSDockNumber"] == ""
        assert item["OCCChartNumber"] == "14240"
        assert item["PrimaryABARoutNumber"] == "21000021"

    def test_filers_since_date_int_to_str(self):
        rest = [480228, 852320, 628403]
        result = DataNormalizer.normalize_response(rest, "RetrieveFilersSinceDate", "REST")
        assert result == ["480228", "852320", "628403"]
        assert all(isinstance(x, str) for x in result)

    def test_reporting_periods_date_normalization(self):
        rest = ["12/31/2023", "6/30/2023"]
        result = DataNormalizer.normalize_response(rest, "RetrieveReportingPeriods", "REST")
        assert result == ["12/31/2023", "6/30/2023"]

    def test_unknown_endpoint_warns_returns_unchanged(self, caplog):
        data = {"foo": "bar"}
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            result = DataNormalizer.normalize_response(data, "UnknownEndpoint", "REST")
        assert result == data
        assert any("UnknownEndpoint" in r.message for r in caplog.records)

    def test_empty_data_returns_unchanged(self):
        assert DataNormalizer.normalize_response(None, "RetrievePanelOfReporters", "REST") is None
        assert DataNormalizer.normalize_response([], "RetrievePanelOfReporters", "REST") == []
        assert DataNormalizer.normalize_response({}, "RetrievePanelOfReporters", "REST") == {}

    def test_soap_protocol_returns_unchanged(self):
        data = [{"ID_RSSD": "480228", "ZIP": "02886"}]
        result = DataNormalizer.normalize_response(data, "RetrievePanelOfReporters", "SOAP")
        assert result is data

    def test_retrieve_facsimile_preserves_binary(self):
        binary = b"\x00\x01\x02\x03"
        result = DataNormalizer.normalize_response(binary, "RetrieveFacsimile", "REST")
        assert result is binary

    def test_ubpr_reporting_periods(self):
        rest = ["3/31/2024", "12/31/2023"]
        result = DataNormalizer.normalize_response(
            rest, "RetrieveUBPRReportingPeriods", "REST"
        )
        assert result == ["3/31/2024", "12/31/2023"]

    def test_filers_submission_datetime(self):
        rest = [{"ID_RSSD": 480228, "SubmissionDateTime": "1/15/2024 3:30:00 PM"}]
        result = DataNormalizer.normalize_response(
            rest, "RetrieveFilersSubmissionDateTime", "REST"
        )
        assert result[0]["ID_RSSD"] == "480228"
        assert result[0]["SubmissionDateTime"] == "1/15/2024 3:30:00 PM"


# ---------------------------------------------------------------------------
# 7. _apply_normalizations
# ---------------------------------------------------------------------------

class TestApplyNormalizations:
    """Tests for the internal normalization dispatch."""

    def test_list_with_array_items(self):
        coercions = {"_array_items": lambda x: str(x)}
        result = DataNormalizer._apply_normalizations([1, 2, 3], coercions, "Test")
        assert result == ["1", "2", "3"]

    def test_list_of_objects(self):
        coercions = {"name": lambda x: x.upper()}
        data = [{"name": "alice"}, {"name": "bob"}]
        result = DataNormalizer._apply_normalizations(data, coercions, "Test")
        assert result[0]["name"] == "ALICE"
        assert result[1]["name"] == "BOB"

    def test_dict_input(self):
        coercions = {"val": lambda x: str(x)}
        result = DataNormalizer._apply_normalizations({"val": 42}, coercions, "Test")
        assert result == {"val": "42"}

    def test_preserve_binary(self):
        coercions = {"_preserve_binary": True}
        data = b"\xff\xfe"
        result = DataNormalizer._apply_normalizations(data, coercions, "Test")
        assert result is data

    def test_simple_value_no_coercion(self):
        coercions = {"field": lambda x: str(x)}
        result = DataNormalizer._apply_normalizations("hello", coercions, "Test")
        assert result == "hello"

    def test_simple_value_with_simple_value_coercion(self):
        coercions = {"_simple_value": lambda x: str(x).upper()}
        result = DataNormalizer._apply_normalizations("hello", coercions, "Test")
        assert result == "HELLO"


# ---------------------------------------------------------------------------
# 8. _normalize_object
# ---------------------------------------------------------------------------

class TestNormalizeObject:
    """Tests for per-object field coercion."""

    def test_coercion_applied(self):
        coercions = {"ID_RSSD": lambda x: str(x)}
        obj = {"ID_RSSD": 480228, "Name": "Bank"}
        result = DataNormalizer._normalize_object(obj, coercions, "test")
        assert result["ID_RSSD"] == "480228"
        assert result["Name"] == "Bank"  # untouched

    def test_missing_field_skipped(self):
        coercions = {"ID_RSSD": lambda x: str(x), "ZIP": lambda x: str(x)}
        obj = {"ID_RSSD": 480228}
        result = DataNormalizer._normalize_object(obj, coercions, "test")
        assert result["ID_RSSD"] == "480228"
        assert "ZIP" not in result

    def test_coercion_failure_keeps_original(self, caplog):
        def bad_coercion(x):
            raise ValueError("boom")

        coercions = {"field": bad_coercion}
        obj = {"field": "original"}
        with caplog.at_level(logging.ERROR, logger="ffiec_data_connect.data_normalizer"):
            result = DataNormalizer._normalize_object(obj, coercions, "ctx")
        assert result["field"] == "original"
        assert any("Failed to normalize" in r.message for r in caplog.records)

    def test_meta_fields_skipped(self):
        coercions = {"_array_items": lambda x: str(x), "real_field": lambda x: x.upper()}
        obj = {"real_field": "hello"}
        result = DataNormalizer._normalize_object(obj, coercions, "test")
        assert result["real_field"] == "HELLO"

    def test_non_dict_input_returned_as_is(self):
        result = DataNormalizer._normalize_object("not a dict", {}, "test")
        assert result == "not a dict"

    def test_original_not_mutated(self):
        coercions = {"val": lambda x: str(x)}
        obj = {"val": 42}
        DataNormalizer._normalize_object(obj, coercions, "test")
        assert obj["val"] == 42  # original unchanged

    def test_unchanged_value_not_counted(self):
        """If coercion returns same value, no update occurs."""
        coercions = {"name": lambda x: x}
        obj = {"name": "Alice"}
        result = DataNormalizer._normalize_object(obj, coercions, "test")
        assert result["name"] == "Alice"


# ---------------------------------------------------------------------------
# 9. _validate_normalized_data
# ---------------------------------------------------------------------------

class TestValidateNormalizedData:
    """Tests for post-normalization validation."""

    def test_valid_data_no_warnings(self, caplog):
        data = [{"ID_RSSD": "480228", "ZIP": "02886", "FDICCertNumber": "1039"}]
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "RetrievePanelOfReporters")
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 0

    def test_invalid_zip_4_digit_warns(self, caplog):
        # A 4-digit string ZIP hits the pattern branch (^\d{5}$ fails) -> "format invalid"
        data = [{"ZIP": "2886"}]
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "Test")
        assert any("format invalid" in r.message for r in caplog.records)

    def test_non_string_id_rssd_warns(self, caplog):
        data = [{"ID_RSSD": 480228}]
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "Test")
        assert any("must be string" in r.message for r in caplog.records)

    def test_empty_data_no_error(self):
        DataNormalizer._validate_normalized_data(None, "Test")
        DataNormalizer._validate_normalized_data([], "Test")
        DataNormalizer._validate_normalized_data({}, "Test")

    def test_dict_input_validated(self, caplog):
        # Dict path: string ZIP "2886" fails the ^\d{5}$ pattern -> "format invalid"
        data = {"ZIP": "2886"}
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "Test")
        assert any("format invalid" in r.message for r in caplog.records)

    def test_non_string_zip_warns(self, caplog):
        # Non-string ZIP hits the elif branch -> "must be string"
        data = [{"ZIP": 2886}]
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "Test")
        assert any("must be string" in r.message for r in caplog.records)

    def test_zip_pattern_mismatch_warns(self, caplog):
        data = [{"ZIP": "1234X"}]
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "Test")
        assert any("format invalid" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# 10. get_normalization_stats
# ---------------------------------------------------------------------------

class TestGetNormalizationStats:
    """Tests for normalization statistics."""

    def test_counts_transformations(self):
        before = {"ID_RSSD": 480228, "ZIP": 2886}
        after = {"ID_RSSD": "480228", "ZIP": "02886"}
        stats = DataNormalizer.get_normalization_stats(before, after, "RetrievePanelOfReporters")
        assert stats["transformations_applied"] >= 2
        assert len(stats["fields_normalized"]) >= 2

    def test_type_changes_tracked(self):
        before = {"ID_RSSD": 480228}
        after = {"ID_RSSD": "480228"}
        stats = DataNormalizer.get_normalization_stats(before, after, "Test")
        assert "int_to_str" in stats["type_changes"]
        assert stats["type_changes"]["int_to_str"] >= 1

    def test_list_data_comparison(self):
        before = [{"ID_RSSD": 480228}]
        after = [{"ID_RSSD": "480228"}]
        stats = DataNormalizer.get_normalization_stats(before, after, "Test")
        assert stats["transformations_applied"] >= 1

    def test_value_change_same_type(self):
        before = {"ZIP": "2886"}
        after = {"ZIP": "02886"}
        stats = DataNormalizer.get_normalization_stats(before, after, "Test")
        assert stats["transformations_applied"] >= 1
        assert any("ZIP" in f for f in stats["fields_normalized"])

    def test_stats_structure(self):
        stats = DataNormalizer.get_normalization_stats({}, {}, "Test")
        assert "endpoint" in stats
        assert "timestamp" in stats
        assert "data_size" in stats
        assert "type_changes" in stats
        assert "validation_passed" in stats

    def test_validation_passed_flag(self):
        before = {"ID_RSSD": "480228"}
        after = {"ID_RSSD": "480228"}
        stats = DataNormalizer.get_normalization_stats(before, after, "Test")
        assert stats["validation_passed"] is True


# ---------------------------------------------------------------------------
# 11. _estimate_data_size
# ---------------------------------------------------------------------------

class TestEstimateDataSize:
    """Tests for data size estimation."""

    def test_list_size(self):
        result = DataNormalizer._estimate_data_size([1, 2, 3])
        assert isinstance(result, int)
        assert result > 0

    def test_dict_size(self):
        result = DataNormalizer._estimate_data_size({"a": 1, "b": 2})
        assert isinstance(result, int)
        assert result > 0

    def test_none_returns_zero(self):
        assert DataNormalizer._estimate_data_size(None) == 0

    def test_string_size(self):
        result = DataNormalizer._estimate_data_size("hello")
        assert result == len("hello")

    def test_empty_list(self):
        result = DataNormalizer._estimate_data_size([])
        assert isinstance(result, int)
        assert result > 0  # len(str([])) == 2


# ---------------------------------------------------------------------------
# 12. _count_object_changes
# ---------------------------------------------------------------------------

class TestCountObjectChanges:
    """Tests for per-object change counting."""

    def test_type_changes(self):
        before = {"ID_RSSD": 480228}
        after = {"ID_RSSD": "480228"}
        stats = {
            "transformations_applied": 0,
            "fields_normalized": [],
            "type_changes": {},
        }
        result = DataNormalizer._count_object_changes(before, after, "root", stats)
        assert result["transformations_applied"] == 1
        assert "int_to_str" in result["type_changes"]

    def test_value_changes_same_type(self):
        before = {"ZIP": "2886"}
        after = {"ZIP": "02886"}
        stats = {
            "transformations_applied": 0,
            "fields_normalized": [],
            "type_changes": {},
        }
        result = DataNormalizer._count_object_changes(before, after, "root", stats)
        assert result["transformations_applied"] == 1
        assert "root.ZIP" in result["fields_normalized"]

    def test_unchanged_fields(self):
        before = {"Name": "Bank"}
        after = {"Name": "Bank"}
        stats = {
            "transformations_applied": 0,
            "fields_normalized": [],
            "type_changes": {},
        }
        result = DataNormalizer._count_object_changes(before, after, "root", stats)
        assert result["transformations_applied"] == 0
        assert len(result["fields_normalized"]) == 0

    def test_multiple_changes(self):
        before = {"ID_RSSD": 1, "ZIP": 2886, "Name": "Bank"}
        after = {"ID_RSSD": "1", "ZIP": "02886", "Name": "Bank"}
        stats = {
            "transformations_applied": 0,
            "fields_normalized": [],
            "type_changes": {},
        }
        result = DataNormalizer._count_object_changes(before, after, "[0]", stats)
        assert result["transformations_applied"] == 2
        assert len(result["fields_normalized"]) == 2

    def test_bool_to_str_tracked(self):
        before = {"flag": True}
        after = {"flag": "true"}
        stats = {
            "transformations_applied": 0,
            "fields_normalized": [],
            "type_changes": {},
        }
        result = DataNormalizer._count_object_changes(before, after, "root", stats)
        assert "bool_to_str" in result["type_changes"]

    def test_field_only_in_before_ignored(self):
        """If a key in before is absent in after, it is not counted."""
        before = {"a": 1, "b": 2}
        after = {"a": "1"}
        stats = {
            "transformations_applied": 0,
            "fields_normalized": [],
            "type_changes": {},
        }
        result = DataNormalizer._count_object_changes(before, after, "root", stats)
        # Only "a" is compared (present in both); "b" is skipped
        assert result["transformations_applied"] == 1


# ---------------------------------------------------------------------------
# Additional coverage tests for data_normalizer.py
# ---------------------------------------------------------------------------
from unittest.mock import patch, Mock


class TestNormalizeResponseFailure:
    """Tests for normalize_response failure path (lines 340-344)."""

    def test_apply_normalizations_exception_returns_original_data(self, caplog):
        """If _apply_normalizations raises, should return original data (lines 340-344)."""
        data = [{"ID_RSSD": 480228}]
        with patch.object(
            DataNormalizer, '_apply_normalizations', side_effect=RuntimeError("boom")
        ):
            with caplog.at_level(logging.ERROR, logger="ffiec_data_connect.data_normalizer"):
                result = DataNormalizer.normalize_response(
                    data, "RetrievePanelOfReporters", "REST"
                )
        assert result is data  # original data returned
        assert any("Failed to normalize" in r.message for r in caplog.records)


class TestValidateObject4DigitZIP:
    """Tests for _validate_object with 4-digit ZIP string (lines 471-472)."""

    def test_4digit_zip_string_produces_error(self):
        """A 4-digit numeric string ZIP should produce a 'missing leading zero' error (lines 471-472)."""
        errors: list = []
        obj = {"ZIP": "2886"}
        # This ZIP passes the pattern check ^\d{5}$ (it fails, len!=5)
        # but doesn't reach the elif. Actually it matches pattern check as
        # "2886" is a 4-char digit string that fails ^\d{5}$, so the
        # "format invalid" error is produced. The 4-digit elif branch is for
        # non-string ZIPs or ZIPs that aren't caught by pattern.
        # Let's test the branch explicitly with a non-matching-pattern case:
        # Actually the ZIP "2886" IS a string and IS 4 digits, but the pattern
        # check fires first (pattern ^\d{5}$ fails). So the elif at 471 is
        # reached only when value is a string but the pattern check above is
        # not triggered. Looking at the code again:
        #   if pattern and isinstance(value, str):
        #       if not re.match(pattern, value):
        #           errors.append format invalid
        #   elif field == "ZIP":
        #       if not isinstance(value, str):  ... line 468
        #       elif len(value) == 4 and value.isdigit():  ... line 471
        # So the elif ZIP branch is reached only if pattern is falsy or value
        # is NOT a string. Since ZIP has a pattern, the elif is reached only
        # when value is not a string. A non-string 4-digit value hits line 468.
        # However if we remove the pattern from VALIDATION_RULES for ZIP temporarily...
        # Actually, let's look more carefully. The code is:
        #   if pattern and isinstance(value, str):
        # If value is NOT a string, this is False, and we fall to elif field == "ZIP"
        # where we check isinstance → hits 468 "must be string".
        # If value IS a string with pattern, we go into the pattern branch.
        # So lines 471-472 are reached when field=="ZIP", isinstance(value, str)==True
        # but pattern is NOT set. But ZIP DOES have a pattern.
        # Wait, re-reading: the elif chain at 465 is only entered when the
        # first `if pattern and isinstance(value, str)` is False.
        # For ZIP with a string value, pattern is truthy and isinstance is True,
        # so it enters the `if` block, not the `elif`. Lines 471-472 are dead
        # code for ZIP when pattern is set. But the test spec says to cover them.
        # Let's temporarily remove the pattern to test:
        original_rules = DataNormalizer.VALIDATION_RULES.copy()
        DataNormalizer.VALIDATION_RULES = {
            "ZIP": {"description": "5-digit ZIP code"},
            "ID_RSSD": original_rules["ID_RSSD"],
            "FDICCertNumber": original_rules["FDICCertNumber"],
        }
        try:
            errors_list: list = []
            DataNormalizer._validate_object(
                {"ZIP": "2886"}, "test", errors_list
            )
            assert any("missing leading zero" in e for e in errors_list)
        finally:
            DataNormalizer.VALIDATION_RULES = original_rules


class TestGetNormalizationStatsException:
    """Tests for get_normalization_stats exception handling (lines 527-529)."""

    def test_exception_during_comparison_adds_error_key(self):
        """Exception during comparison should set error key in stats (lines 527-529)."""
        with patch.object(
            DataNormalizer, '_count_object_changes', side_effect=RuntimeError("comparison fail")
        ):
            stats = DataNormalizer.get_normalization_stats(
                {"ID_RSSD": 480228},
                {"ID_RSSD": "480228"},
                "Test"
            )
        assert "error" in stats
        assert "comparison fail" in stats["error"]


class TestValidateNormalizedDataErrorAccumulation:
    """Tests for validation error accumulation (lines 447-448)."""

    def test_validation_exception_caught(self, caplog):
        """Exception during validation should be caught and logged (lines 447-448)."""
        # Create data that will cause _validate_object to raise
        with patch.object(
            DataNormalizer, '_validate_object', side_effect=RuntimeError("validate boom")
        ):
            with caplog.at_level(logging.ERROR, logger="ffiec_data_connect.data_normalizer"):
                DataNormalizer._validate_normalized_data(
                    [{"ID_RSSD": "123"}], "Test"
                )
        assert any("Validation failed" in r.message for r in caplog.records)

    def test_multiple_validation_errors_logged(self, caplog):
        """Multiple validation issues should be accumulated and logged (line 444-445)."""
        data = [
            {"ID_RSSD": 480228, "ZIP": 2886},
            {"ID_RSSD": 12345, "ZIP": 1234},
            {"ID_RSSD": 99999, "ZIP": 567},
        ]
        with caplog.at_level(logging.WARNING, logger="ffiec_data_connect.data_normalizer"):
            DataNormalizer._validate_normalized_data(data, "Test")
        # Should log warnings about multiple issues
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) >= 1
        # The warning message should contain error summaries
        assert any("Validation warnings" in r.message for r in warnings)


class TestValidatePydanticCompatibilityException:
    """Tests for exception in validate_pydantic_compatibility (lines 286-288)."""

    def test_exception_sets_error_and_incompatible(self):
        """Exception during validation should set error and compatible=False (lines 286-288)."""
        # Pass data that will cause an exception in the validation loop
        # We can mock the isinstance check to raise
        class BadList:
            """A list-like object that raises on iteration."""
            def __iter__(self):
                raise RuntimeError("iteration boom")

        # Actually, let's just patch the internal check to raise
        bad_data = Mock()
        bad_data.__iter__ = Mock(side_effect=RuntimeError("bad iteration"))
        # The code checks isinstance(data, list) first, so we need actual list behavior
        # Use a proper approach: patch something inside the method
        with patch('builtins.isinstance', side_effect=lambda obj, cls: (_ for _ in ()).throw(RuntimeError("type check boom")) if cls == list and obj is bad_data else isinstance.__wrapped__(obj, cls) if hasattr(isinstance, '__wrapped__') else type(obj) == cls or issubclass(type(obj), cls)):
            # This approach is too fragile, let's use a simpler method
            pass

        # Simpler approach: create data whose enumeration raises inside the try block
        class ExplodingDict(dict):
            def __getitem__(self, key):
                if key == "ID_RSSD":
                    raise RuntimeError("kaboom")
                return super().__getitem__(key)
            def __contains__(self, key):
                if key == "ID_RSSD":
                    raise RuntimeError("kaboom")
                return super().__contains__(key)

        data = [ExplodingDict({"Name": "Bank"})]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        assert report["compatible"] is False
        assert "error" in report
        assert "kaboom" in report["error"]


# ---------------------------------------------------------------------------
# Branch-partial coverage tests for data_normalizer.py
# ---------------------------------------------------------------------------


class TestValidatePydanticBranchPartials:
    """Tests for branch-partial misses in validate_pydantic_compatibility."""

    def test_panel_reporters_dict_not_list_skips_validation(self):
        """246->290: RetrievePanelOfReporters with dict input (not list) skips loop."""
        data = {"ID_RSSD": "12345", "Name": "Bank"}
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        # dict is not a list, so the if-isinstance(data, list) is False -> skip to 290
        assert report["compatible"] is True
        assert len(report["warnings"]) == 0

    def test_panel_reporters_list_with_non_dict_item(self):
        """248->247: Loop item that is NOT a dict should be skipped."""
        data = ["not_a_dict", 12345, None]
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrievePanelOfReporters"
        )
        # Non-dict items skip the inner isinstance(item, dict) check
        assert report["compatible"] is True
        assert len(report["warnings"]) == 0

    def test_filers_since_date_dict_not_list_skips_validation(self):
        """278->290: RetrieveFilersSinceDate with dict input (not list) skips loop."""
        data = {"some_key": "some_value"}
        report = DataNormalizer.validate_pydantic_compatibility(
            data, "RetrieveFilersSinceDate"
        )
        # dict is not a list, so isinstance(data, list) is False -> skip to 290
        assert report["compatible"] is True
        assert len(report["warnings"]) == 0


class TestValidateObjectBranchPartials:
    """Tests for branch-partial misses in _validate_object."""

    def test_zip_non_string_produces_error(self):
        """471->454: ZIP field where value is NOT a string."""
        errors: list = []
        DataNormalizer._validate_object({"ZIP": 2886}, "test", errors)
        assert any("must be string" in e for e in errors)

    def test_id_rssd_valid_string_passes(self):
        """475->454: ID_RSSD where value IS a string passes validation (no error)."""
        errors: list = []
        DataNormalizer._validate_object({"ID_RSSD": "480228"}, "test", errors)
        # A valid string ID_RSSD should produce no errors
        rssd_errors = [e for e in errors if "ID_RSSD" in e]
        assert len(rssd_errors) == 0

    def test_id_rssd_non_string_produces_error(self):
        """477->454: ID_RSSD where value is NOT a string."""
        errors: list = []
        DataNormalizer._validate_object({"ID_RSSD": 480228}, "test", errors)
        assert any("must be string" in e for e in errors)


class TestGetNormalizationStatsDictBranch:
    """Tests for get_normalization_stats dict before/after branch (516->524)."""

    def test_dict_before_and_after(self):
        """516->524: isinstance(data_before, dict) branch with dict data."""
        before = {"ID_RSSD": 480228, "ZIP": 2886}
        after = {"ID_RSSD": "480228", "ZIP": "02886"}
        stats = DataNormalizer.get_normalization_stats(before, after, "Test")
        assert stats["transformations_applied"] >= 2
        assert len(stats["fields_normalized"]) >= 2
        assert stats["validation_passed"] is True


class TestValidateObjectFDICCertNumberFallthrough:
    """Cover 478->454: field is in VALIDATION_RULES but isn't ZIP or ID_RSSD — falls through loop."""

    def test_fdic_cert_number_non_string_falls_through_elif_chain(self):
        """FDICCertNumber is in VALIDATION_RULES with a pattern. A non-string value skips the
        first `if pattern and isinstance(value, str)` branch, then reaches the ZIP elif (False)
        and the ID_RSSD elif (False), exiting the outer if back to the loop head. No error appended.
        """
        errors: list = []
        DataNormalizer._validate_object({"FDICCertNumber": 12345}, "test", errors)
        # No error about FDICCertNumber — this field has no non-string error path in _validate_object,
        # and the pattern-check path is skipped because value isn't a string.
        assert not any("FDICCertNumber" in e for e in errors)


class TestGetNormalizationStatsNeitherListNorDict:
    """Cover 520->528: data_before/after are neither both lists nor both dicts."""

    def test_mixed_types_skips_count_branches(self):
        """When `before` and `after` don't match either the list/list or dict/dict branches
        (e.g., both strings), the elif at line 520 evaluates False and control jumps past both
        count-branches to the validation step at line 528. No count_object_changes happens, but
        stats are still returned without raising."""
        before = "not-a-list-or-dict"
        after = "also-not-a-list-or-dict"
        stats = DataNormalizer.get_normalization_stats(before, after, "Test")
        # Stats should still return a structured dict even for non-comparable types.
        assert isinstance(stats, dict)
        assert stats["endpoint"] == "Test"
        # No transformations were counted because neither branch matched.
        assert stats["transformations_applied"] == 0
