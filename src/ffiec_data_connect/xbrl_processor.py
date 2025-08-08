"""Internal functions used to process XBRL data received from the FFIEC Webservice

This module provides secure XML/XBRL processing with XXE attack prevention.
"""
from itertools import chain
from datetime import datetime
import re
from typing import Dict, List, Any, Optional

# Use defusedxml for secure XML parsing (prevents XXE attacks)
try:
    import defusedxml.ElementTree as ET
    from defusedxml import defuse_stdlib
    # Defuse standard library XML modules
    defuse_stdlib()
    import xmltodict
    SECURE_XML = True
except ImportError:
    # Fallback to standard library with warning
    import xml.etree.ElementTree as ET
    import xmltodict
    import warnings
    warnings.warn(
        "defusedxml not installed - XML parsing may be vulnerable to XXE attacks. "
        "Install with: pip install defusedxml",
        SecurityWarning,
        stacklevel=2
    )
    SECURE_XML = False

from ffiec_data_connect.exceptions import XMLParsingError, raise_exception

re_date = re.compile('[0-9]{4}\-[0-9]{2}\-[0-9]{2}')

def _process_xml(data: bytes, output_date_format: str) -> List[Dict[str, Any]]:
    """Process XBRL XML data securely with XXE prevention.
    
    Args:
        data: Raw XML bytes from FFIEC webservice
        output_date_format: Format for date output ('string_original', 'string_yyyymmdd', 'python_format')
    
    Returns:
        List of processed data dictionaries
        
    Raises:
        XMLParsingError: If XML parsing fails
    """
    if not data:
        raise_exception(
            XMLParsingError,
            "Empty XML data received",
            "Empty XML data received from FFIEC webservice"
        )
    
    try:
        # Secure XML parsing with XXE prevention
        decoded_data = data.decode('utf-8')
        
        # Parse with xmltodict (which uses defused XML if available)
        parsed_data = xmltodict.parse(decoded_data)
        
        if 'xbrl' not in parsed_data:
            raise_exception(
                XMLParsingError,
                "Invalid XBRL format",
                "Invalid XBRL format: missing 'xbrl' root element",
                xml_snippet=decoded_data[:500]
            )
        
        dict_data = parsed_data['xbrl']
        
    except UnicodeDecodeError as e:
        raise_exception(
            XMLParsingError,
            f"Failed to decode XML data: {str(e)}",
            f"Failed to decode XML data: {str(e)}. Data may be corrupted or in wrong encoding."
        )
    except Exception as e:
        raise_exception(
            XMLParsingError,
            f"Failed to parse XML/XBRL data: {str(e)}",
            f"Failed to parse XML/XBRL data: {str(e)}",
            xml_snippet=data[:500].decode('utf-8', errors='ignore') if data else None
        )

    keys_to_parse = list(filter(lambda x: 'cc:' in x, dict_data.keys())) + list(filter(lambda x: 'uc:' in x, dict_data.keys()))
    parsed_data = list(chain.from_iterable(filter(None,list(map(lambda x: _process_xbrl_item(x, dict_data[x], output_date_format),keys_to_parse,)))))
    ret_data = []
    for row in parsed_data:
        new_dict = {}
        new_dict.update({'mdrm':row['mdrm']})
        new_dict.update({'rssd':row['rssd']})
        new_dict.update({'quarter':row['quarter']})
        if row['data_type'] == 'int':
            new_dict.update({'int_data':int(row['value'])})
            new_dict.update({'float_data':None})
            new_dict.update({'bool_data':None})
            new_dict.update({'str_data':None})
            new_dict.update({'data_type':row['data_type']})

        elif row['data_type'] == 'float':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':row['value']})
            new_dict.update({'bool_data':None})
            new_dict.update({'str_data':None})
            new_dict.update({'data_type':row['data_type']})

        elif row['data_type'] == 'str':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':None})
            new_dict.update({'bool_data':None})
            new_dict.update({'str_data':row['value']})
            new_dict.update({'data_type':row['data_type']})

        elif row['data_type'] == 'float':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':row['value']})
            new_dict.update({'bool_data':None})
            new_dict.update({'data_type':row['data_type']})
            new_dict.update({'str_data':None})

        elif row['data_type'] == 'bool':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':None})
            new_dict.update({'bool_data':row['value']})
            new_dict.update({'data_type':row['data_type']})
            new_dict.update({'str_data':None})

        ret_data.append(new_dict)
    
    return ret_data


def _create_ffiec_date_from_datetime(indate: datetime) -> str:
    """Converts a datetime object to a FFIEC-formatted date

    Args:
        indate (datetime): the date to convert

    Returns:
        str: the date in FFIEC format
    """
    month_str = str(indate.month)
    day_str = str(indate.day)
    year_str = str(indate.year)
    
    mmddyyyy = month_str + "/" + day_str + "/" + year_str
    
    return mmddyyyy

def _process_xbrl_item(name, items, date_format):
    # incoming is a data dictionary
    results = []
    if type(items) != list:
        items = [items]
    for j,item in enumerate(items):
        context = item.get('@contextRef')
        unit_type = item.get('@unitRef')
        value = item.get('#text')
        mdrm = name.replace("cc:","").replace("uc:","")
        rssd = context.split('_')[1]
        #date = int(context.split('_')[2].replace("-",''))

        quarter = re_date.findall(context)[0]

        # transform the date to the requested date format
        if date_format == 'string_original':
            quarter = _create_ffiec_date_from_datetime(datetime.strptime(quarter, '%Y-%m-%d'))
        elif date_format == 'string_yyyymmdd':
            quarter = datetime.strptime(quarter, '%Y-%m-%d').strftime('%Y%m%d')
        elif date_format == 'python_format':
            quarter = datetime.strptime(quarter, '%Y-%m-%d')
        
        data_type = None


        if unit_type == 'USD':
            value = int(value)/1000
            data_type = 'int'
        elif unit_type == 'PURE':
            value = float(value)
            data_type = 'float'
        elif unit_type == 'NON-MONETARY':
            value = float(value)
            data_type = 'float'
        elif value == 'true':
            value = True
            data_type = 'bool'
        elif value == 'false':
            value = False
            data_type = 'bool'
        else:
            data_type = 'str'                

        results.append({'mdrm':mdrm, 'rssd':rssd, 'value':value, 'data_type':data_type, 'quarter':quarter})

    return results
