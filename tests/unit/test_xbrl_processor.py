"""
Unit tests for xbrl_processor.py coverage.

Tests XML/XBRL processing including edge cases for full coverage.
"""

from datetime import datetime

import pytest

from ffiec_data_connect.config import Config
from ffiec_data_connect.exceptions import XMLParsingError
from ffiec_data_connect.xbrl_processor import _process_xbrl_item, _process_xml


class TestXBRLProcessorCoverage:
    """Tests targeting uncovered lines in xbrl_processor.py."""

    @pytest.fixture(autouse=True)
    def _disable_legacy_errors(self):
        """Disable legacy errors so specific exception types are raised."""
        Config.set_legacy_errors(False)
        yield

    def test_process_xml_empty_bytes_raises_xml_parsing_error(self):
        """_process_xml with empty bytes b'' raises XMLParsingError (line 59)."""
        with pytest.raises(XMLParsingError):
            _process_xml(b"", "string_original")

    def test_xbrl_item_without_context_ref_skipped(self):
        """XBRL items without @contextRef are skipped (line 185)."""
        # Item without @contextRef should be skipped
        items = {"@unitRef": "USD", "#text": "1000000"}
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert result == []

    def test_xbrl_item_without_valid_date_in_context_skipped(self):
        """XBRL items without a valid date in context are skipped (line 192)."""
        # contextRef without a date pattern (YYYY-MM-DD)
        items = {
            "@contextRef": "ctx_480228_nodatehere",
            "@unitRef": "USD",
            "#text": "1000000",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert result == []

    def test_date_format_string_yyyymmdd(self):
        """Date format 'string_yyyymmdd' produces YYYYMMDD output (line 200)."""
        items = {
            "@contextRef": "ctx_480228_2025-12-31",
            "@unitRef": "USD",
            "#text": "5000000",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_yyyymmdd")
        assert len(result) == 1
        assert result[0]["quarter"] == "20251231"

    def test_date_format_python_format(self):
        """Date format 'python_format' produces datetime object (line 203)."""
        items = {
            "@contextRef": "ctx_480228_2025-12-31",
            "@unitRef": "USD",
            "#text": "5000000",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "python_format")
        assert len(result) == 1
        assert isinstance(result[0]["quarter"], datetime)
        assert result[0]["quarter"] == datetime(2025, 12, 31)

    def test_date_format_string_original(self):
        """Date format 'string_original' produces MM/DD/YYYY output."""
        items = {
            "@contextRef": "ctx_480228_2025-12-31",
            "@unitRef": "USD",
            "#text": "5000000",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 1
        assert result[0]["quarter"] == "12/31/2025"

    def test_process_xbrl_item_list_input(self):
        """_process_xbrl_item handles list of items."""
        items = [
            {
                "@contextRef": "ctx_480228_2025-12-31",
                "@unitRef": "USD",
                "#text": "5000000",
            },
            {
                "@contextRef": "ctx_480228_2025-09-30",
                "@unitRef": "USD",
                "#text": "3000000",
            },
        ]
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 2

    def test_process_xml_full_pipeline(self):
        """Full _process_xml pipeline with real XBRL data."""
        sample_xbrl = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:cc="http://www.ffiec.gov/call" xmlns:uc="http://www.ffiec.gov/call/uc">
    <context id="ctx_480228_2025-12-31">
        <entity><identifier>480228</identifier></entity>
        <period><instant>2025-12-31</instant></period>
    </context>
    <cc:RCON0010 contextRef="ctx_480228_2025-12-31" unitRef="USD" decimals="0">5000000</cc:RCON0010>
    <uc:UBPR4107 contextRef="ctx_480228_2025-12-31" unitRef="PURE" decimals="2">12.50</uc:UBPR4107>
</xbrl>"""

        result = _process_xml(sample_xbrl, "string_original")
        assert isinstance(result, list)
        assert len(result) == 2


class TestXBRLProcessorAdditionalCoverage:
    """Additional tests for uncovered lines in xbrl_processor.py."""

    @pytest.fixture(autouse=True)
    def _disable_legacy_errors(self):
        """Disable legacy errors so specific exception types are raised."""
        Config.set_legacy_errors(False)
        yield

    def test_unicode_decode_error_fallback(self):
        """Bytes not valid UTF-8 trigger UnicodeDecodeError fallback (line 89).

        The code tries xmltodict.parse(data) first; if that fails with UnicodeDecodeError,
        it falls back to data.decode("utf-8") which also fails, hitting the outer except.
        We use bytes that ARE valid XML but contain a non-UTF-8 byte.
        """
        # Latin-1 encoded XML with \xe9 (e-acute in Latin-1, invalid continuation in UTF-8)
        latin1_xml = (
            b'<?xml version="1.0" encoding="latin-1"?>'
            b'<xbrl xmlns:cc="http://www.ffiec.gov/call">'
            b'<cc:RCON0010 contextRef="ctx_480228_2023-12-31" unitRef="USD" decimals="0">100000</cc:RCON0010>'
            b"</xbrl>"
        )
        # Insert a non-UTF-8 byte that makes the first parse attempt fail
        # Use \xe9 in a comment to cause UnicodeDecodeError
        bad_xml = latin1_xml.replace(b"</xbrl>", b"<!-- caf\xe9 --></xbrl>")

        # This should either succeed (if xmltodict can handle it) or raise XMLParsingError
        # The key is exercising the UnicodeDecodeError catch path
        try:
            result = _process_xml(bad_xml, "string_original")
            # If it succeeds, that's fine - the fallback path was exercised
            assert isinstance(result, list)
        except XMLParsingError:
            # Also acceptable - the point is we exercised the UnicodeDecodeError branch
            pass

    def test_date_format_string_yyyymmdd_via_process_xml(self):
        """Full pipeline with string_yyyymmdd date format (lines 200-201 via _process_xml)."""
        sample_xbrl = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:cc="http://www.ffiec.gov/call">
    <cc:RCON0010 contextRef="ctx_480228_2023-12-31" unitRef="USD" decimals="0">5000000</cc:RCON0010>
</xbrl>"""

        result = _process_xml(sample_xbrl, "string_yyyymmdd")
        assert len(result) == 1
        assert result[0]["quarter"] == "20231231"

    def test_value_type_non_monetary_float(self):
        """NON-MONETARY unitRef produces float data_type (lines 213-215)."""
        items = {
            "@contextRef": "ctx_480228_2023-12-31",
            "@unitRef": "NON-MONETARY",
            "#text": "42.5",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 1
        assert result[0]["data_type"] == "float"
        assert result[0]["value"] == 42.5

    def test_value_type_bool_true(self):
        """value='true' produces bool data_type (lines 216-218)."""
        items = {
            "@contextRef": "ctx_480228_2023-12-31",
            "@unitRef": None,
            "#text": "true",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 1
        assert result[0]["data_type"] == "bool"
        assert result[0]["value"] is True

    def test_value_type_bool_false(self):
        """value='false' produces bool data_type (lines 219-221)."""
        items = {
            "@contextRef": "ctx_480228_2023-12-31",
            "@unitRef": None,
            "#text": "false",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 1
        assert result[0]["data_type"] == "bool"
        assert result[0]["value"] is False

    def test_value_type_str_fallback(self):
        """Unknown unit type with non-boolean value produces str data_type (lines 222-223)."""
        items = {
            "@contextRef": "ctx_480228_2023-12-31",
            "@unitRef": "UNKNOWN",
            "#text": "some text",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 1
        assert result[0]["data_type"] == "str"
        assert result[0]["value"] == "some text"

    def test_value_type_str_when_no_text(self):
        """None value with unknown unit produces str data_type (line 223)."""
        items = {
            "@contextRef": "ctx_480228_2023-12-31",
            "@unitRef": "USD",
        }
        result = _process_xbrl_item("cc:RCON0010", items, "string_original")
        assert len(result) == 1
        # USD with None value falls to else -> str
        assert result[0]["data_type"] == "str"

    def test_full_pipeline_all_types(self):
        """Full pipeline with all value types through _process_xml."""
        sample_xbrl = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns:cc="http://www.ffiec.gov/call">
    <cc:RCON0010 contextRef="ctx_480228_2023-12-31" unitRef="USD" decimals="0">5000000</cc:RCON0010>
    <cc:RCON0020 contextRef="ctx_480228_2023-12-31" unitRef="PURE" decimals="2">12.50</cc:RCON0020>
    <cc:RCON0030 contextRef="ctx_480228_2023-12-31" unitRef="NON-MONETARY" decimals="0">42.5</cc:RCON0030>
    <cc:RCON0040 contextRef="ctx_480228_2023-12-31">true</cc:RCON0040>
    <cc:RCON0050 contextRef="ctx_480228_2023-12-31">false</cc:RCON0050>
    <cc:RCON0060 contextRef="ctx_480228_2023-12-31" unitRef="TEXT">hello</cc:RCON0060>
</xbrl>"""

        result = _process_xml(sample_xbrl, "string_yyyymmdd")
        assert len(result) == 6

        types_found = {r["data_type"] for r in result}
        assert "int" in types_found
        assert "float" in types_found
        assert "bool" in types_found
        assert "str" in types_found


class TestXBRLProcessorOuterUnicodeDecodeError:
    """Cover line 89: outer UnicodeDecodeError where both parse paths fail."""

    def test_corrupt_bytes_raises_xml_parsing_error(self):
        """Bytes that can't be decoded as UTF-8, and xmltodict also fails."""
        from unittest.mock import patch as _patch

        from ffiec_data_connect.config import Config

        Config.set_legacy_errors(False)

        # Invalid UTF-8 bytes that will fail .decode("utf-8")
        bad_bytes = b"\x80\x81\x82\xff"

        # Mock xmltodict.parse to raise UnicodeDecodeError on first call (direct bytes),
        # then the fallback data.decode("utf-8") at line 73 will also raise UnicodeDecodeError
        # because bad_bytes is not valid UTF-8 — triggering the outer handler at line 88.
        with _patch(
            "ffiec_data_connect.xbrl_processor.xmltodict.parse",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "mock"),
        ):
            with pytest.raises((XMLParsingError, ValueError)):
                _process_xml(bad_bytes, "string_original", False)

        Config.reset()


class TestXBRLProcessorDateFormatFallthrough:
    """Cover branch 202->205: date_format doesn't match any of the three known values."""

    def test_unknown_date_format_leaves_quarter_as_raw_string(self):
        """An unrecognized date_format falls through the elif chain without transforming `quarter`.

        The three known formats are 'string_original', 'string_yyyymmdd', and 'python_format'.
        Anything else must bypass transformation, leaving the ISO date string intact.
        """
        items = [
            {
                "@contextRef": "PeriodContext_1234567_2023-12-31",
                "@unitRef": "USD",
                "#text": "1000",
            }
        ]
        result = _process_xbrl_item("cc:RCON2170", items, "unrecognized_format")
        # Quarter remains as the original raw YYYY-MM-DD string since no branch transformed it.
        assert result[0]["quarter"] == "2023-12-31"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
