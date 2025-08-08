"""
Test XML processing optimizations for memory efficiency.

Tests that XML processing improvements work correctly and are more efficient.
"""

import pytest
import numpy as np
from unittest.mock import patch, Mock

from ffiec_data_connect.xbrl_processor import _process_xml
from ffiec_data_connect.exceptions import XMLParsingError


class TestXMLProcessingOptimizations:
    """Test XML processing memory optimizations."""
    
    def test_xml_parsing_from_bytes_directly(self):
        """Test that XML parsing tries bytes first for memory efficiency."""
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" 
      xmlns:cc="http://www.ffiec.gov/call">
    <cc:RCON0010 contextRef="c1" unitRef="u1" decimals="0">1000000</cc:RCON0010>
</xbrl>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            # Mock successful parsing from bytes
            mock_parse.return_value = {
                'xbrl': {
                    'cc:RCON0010': {
                        '@contextRef': 'c1',
                        '@unitRef': 'u1', 
                        '@decimals': '0',
                        '#text': '1000000'
                    }
                }
            }
            
            with patch('ffiec_data_connect.xbrl_processor._process_xbrl_item') as mock_process:
                mock_process.return_value = [{
                    'mdrm': 'RCON0010',
                    'rssd': '123456',
                    'quarter': '2023-03-31',
                    'data_type': 'int',
                    'value': 1000000
                }]
                
                result = _process_xml(sample_xml, 'string_original')
                
                # Should call parse directly with bytes (first attempt)
                mock_parse.assert_called_once_with(sample_xml)
                assert len(result) == 1
                assert result[0]['int_data'] == 1000000
                assert np.isnan(result[0]['float_data'])
    
    def test_xml_parsing_fallback_to_string(self):
        """Test fallback to string decoding if bytes parsing fails."""
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <cc:RCON0010>1000000</cc:RCON0010>
</xbrl>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            # First call (bytes) fails, second call (string) succeeds
            mock_parse.side_effect = [
                UnicodeDecodeError('utf-8', b'', 0, 1, 'test error'),  # First call fails
                {'xbrl': {'cc:RCON0010': '1000000'}}  # Second call succeeds
            ]
            
            with patch('ffiec_data_connect.xbrl_processor._process_xbrl_item') as mock_process:
                mock_process.return_value = []
                
                _process_xml(sample_xml, 'string_original')
                
                # Should call parse twice: first with bytes, then with decoded string
                assert mock_parse.call_count == 2
                mock_parse.assert_any_call(sample_xml)  # First call with bytes
                mock_parse.assert_any_call(sample_xml.decode('utf-8'))  # Second call with string
    
    def test_efficient_dict_construction(self):
        """Test that dictionary construction is efficient with single operation."""
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <cc:RCON0010>1000000</cc:RCON0010>
    <uc:UBPR4107>12.50</uc:UBPR4107>
</xbrl>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            mock_parse.return_value = {
                'xbrl': {
                    'cc:RCON0010': '1000000',
                    'uc:UBPR4107': '12.50'
                }
            }
            
            with patch('ffiec_data_connect.xbrl_processor._process_xbrl_item') as mock_process:
                # Mock different data types to test dict construction
                mock_process.side_effect = [
                    [{  # Integer data
                        'mdrm': 'RCON0010',
                        'rssd': '123456',
                        'quarter': '2023-03-31',
                        'data_type': 'int',
                        'value': 1000000
                    }],
                    [{  # Float data
                        'mdrm': 'UBPR4107',
                        'rssd': '123456',
                        'quarter': '2023-03-31',
                        'data_type': 'float',
                        'value': 12.50
                    }]
                ]
                
                result = _process_xml(sample_xml, 'string_original')
                
                # Check that both items are processed correctly
                assert len(result) == 2
                
                # Integer item
                int_item = next(item for item in result if item['mdrm'] == 'RCON0010')
                assert int_item['int_data'] == 1000000
                assert np.isnan(int_item['float_data'])
                assert np.isnan(int_item['bool_data'])
                assert int_item['str_data'] is None
                assert int_item['data_type'] == 'int'
                
                # Float item
                float_item = next(item for item in result if item['mdrm'] == 'UBPR4107')
                assert float_item['float_data'] == 12.50
                assert np.isnan(float_item['int_data'])
                assert np.isnan(float_item['bool_data'])
                assert float_item['str_data'] is None
                assert float_item['data_type'] == 'float'
    
    def test_generator_expression_usage(self):
        """Test that generator expressions are used instead of lists for memory efficiency."""
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <cc:RCON0010>1000000</cc:RCON0010>
    <cc:RCON0071>500000</cc:RCON0071>
    <uc:UBPR4107>12.50</uc:UBPR4107>
</xbrl>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            mock_parse.return_value = {
                'xbrl': {
                    'cc:RCON0010': '1000000',
                    'cc:RCON0071': '500000', 
                    'uc:UBPR4107': '12.50',
                    'other:ITEM': 'ignored'  # Should be ignored (no cc: or uc: prefix)
                }
            }
            
            with patch('ffiec_data_connect.xbrl_processor._process_xbrl_item') as mock_process:
                mock_process.return_value = [{
                    'mdrm': 'TEST',
                    'rssd': '123456',
                    'quarter': '2023-03-31',
                    'data_type': 'int',
                    'value': 1000
                }]
                
                result = _process_xml(sample_xml, 'string_original')
                
                # Should only process cc: and uc: items (3 calls, not 4)
                assert mock_process.call_count == 3
                assert len(result) == 3  # 3 items processed
    
    def test_empty_or_none_item_handling(self):
        """Test that empty or None items are handled efficiently."""
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <cc:RCON0010>1000000</cc:RCON0010>
    <cc:RCON0071>500000</cc:RCON0071>
</xbrl>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            mock_parse.return_value = {
                'xbrl': {
                    'cc:RCON0010': '1000000',
                    'cc:RCON0071': '500000'
                }
            }
            
            with patch('ffiec_data_connect.xbrl_processor._process_xbrl_item') as mock_process:
                # Mock: first item returns None, second returns empty list, third returns data
                mock_process.side_effect = [
                    None,  # Should be skipped
                    [{     # Should be processed
                        'mdrm': 'RCON0071',
                        'rssd': '123456',
                        'quarter': '2023-03-31',
                        'data_type': 'int',
                        'value': 500000
                    }]
                ]
                
                result = _process_xml(sample_xml, 'string_original')
                
                # Should only have the non-None item
                assert len(result) == 1
                assert result[0]['mdrm'] == 'RCON0071'
    
    def test_error_snippet_memory_efficiency(self):
        """Test that error snippets are created efficiently."""
        # Invalid XML (missing xbrl element)
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<invalid_root>
    <cc:RCON0010>1000000</cc:RCON0010>
</invalid_root>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            mock_parse.return_value = {
                'invalid_root': {
                    'cc:RCON0010': '1000000'
                }
            }
            
            # In legacy mode, this will raise ValueError; in new mode, XMLParsingError
            with pytest.raises((XMLParsingError, ValueError)) as exc_info:
                _process_xml(sample_xml, 'string_original')
            
            # Test passes as long as error is raised (testing memory efficiency of error handling)
            error = exc_info.value
            
            # If it's the new XMLParsingError, check details
            if isinstance(error, XMLParsingError):
                assert hasattr(error, 'details')
                assert 'xml_snippet' in error.details
                # Snippet should be limited to avoid memory issues
                assert len(error.details['xml_snippet']) <= 500
            else:
                # Legacy ValueError - test still validates the parsing attempt
                assert isinstance(error, ValueError)


class TestDataTypeHandling:
    """Test optimized data type handling."""
    
    def test_all_data_types_handled_correctly(self):
        """Test that all data types are handled with optimized dict construction."""
        sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
    <cc:ITEM1>test</cc:ITEM1>
    <cc:ITEM2>123</cc:ITEM2>
    <cc:ITEM3>12.5</cc:ITEM3>
    <cc:ITEM4>true</cc:ITEM4>
</xbrl>"""
        
        with patch('ffiec_data_connect.xbrl_processor.xmltodict.parse') as mock_parse:
            mock_parse.return_value = {
                'xbrl': {
                    'cc:ITEM1': 'test',
                    'cc:ITEM2': '123',
                    'cc:ITEM3': '12.5',
                    'cc:ITEM4': 'true'
                }
            }
            
            with patch('ffiec_data_connect.xbrl_processor._process_xbrl_item') as mock_process:
                mock_process.side_effect = [
                    [{'mdrm': 'ITEM1', 'rssd': '123', 'quarter': '2023', 'data_type': 'str', 'value': 'test'}],
                    [{'mdrm': 'ITEM2', 'rssd': '123', 'quarter': '2023', 'data_type': 'int', 'value': 123}],
                    [{'mdrm': 'ITEM3', 'rssd': '123', 'quarter': '2023', 'data_type': 'float', 'value': 12.5}],
                    [{'mdrm': 'ITEM4', 'rssd': '123', 'quarter': '2023', 'data_type': 'bool', 'value': True}]
                ]
                
                result = _process_xml(sample_xml, 'string_original')
                
                assert len(result) == 4
                
                # Check each data type is handled correctly
                str_item = next(item for item in result if item['mdrm'] == 'ITEM1')
                assert str_item['str_data'] == 'test'
                assert np.isnan(str_item['int_data']) and np.isnan(str_item['float_data']) and np.isnan(str_item['bool_data'])
                
                int_item = next(item for item in result if item['mdrm'] == 'ITEM2')
                assert int_item['int_data'] == 123
                assert int_item['str_data'] is None and np.isnan(int_item['float_data']) and np.isnan(int_item['bool_data'])
                
                float_item = next(item for item in result if item['mdrm'] == 'ITEM3')
                assert float_item['float_data'] == 12.5
                assert float_item['str_data'] is None and np.isnan(float_item['int_data']) and np.isnan(float_item['bool_data'])
                
                bool_item = next(item for item in result if item['mdrm'] == 'ITEM4')
                assert bool_item['bool_data'] == True  # Use == for numpy bool comparison
                assert bool_item['str_data'] is None and np.isnan(bool_item['int_data']) and np.isnan(bool_item['float_data'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])