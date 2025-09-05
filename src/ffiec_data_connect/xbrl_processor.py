"""Internal functions used to process XBRL data received from the FFIEC Webservice

This module provides secure XML/XBRL processing with XXE attack prevention.
"""

import re
from datetime import datetime
from itertools import chain
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd

# Use defusedxml for secure XML parsing (prevents XXE attacks)
try:
    from defusedxml import defuse_stdlib

    # Defuse standard library XML modules
    defuse_stdlib()
    import xmltodict

    SECURE_XML = True
except ImportError:
    # Fallback to standard library with warning
    import warnings

    import xmltodict

    warnings.warn(
        "defusedxml not installed - XML parsing may be vulnerable to XXE attacks. "
        "Install with: pip install defusedxml",
        UserWarning,
        stacklevel=2,
    )
    SECURE_XML = False

from ffiec_data_connect.exceptions import XMLParsingError, raise_exception

re_date = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _process_xml(
    data: bytes, output_date_format: str, use_rest_nulls: bool = False
) -> List[Dict[str, Any]]:
    """Process XBRL XML data securely with XXE prevention.

    Args:
        data: Raw XML bytes from FFIEC webservice
        output_date_format: Format for date output ('string_original', 'string_yyyymmdd', 'python_format')
        use_rest_nulls: If True, use pd.NA for REST API compatibility; if False, use np.nan for SOAP compatibility

    Returns:
        List of processed data dictionaries

    Raises:
        XMLParsingError: If XML parsing fails
    """
    if not data:
        raise_exception(
            XMLParsingError,
            "Empty XML data received",
            "Empty XML data received from FFIEC webservice",
        )

    try:
        # Secure XML parsing with XXE prevention - optimize memory usage
        # Try parsing directly from bytes first (more memory efficient)
        try:
            # Direct parsing from bytes avoids creating intermediate string
            parsed_data = xmltodict.parse(data)
        except (UnicodeDecodeError, TypeError):
            # Fallback to string decoding only if direct parsing fails
            decoded_data = data.decode("utf-8")
            parsed_data = xmltodict.parse(decoded_data)

        if "xbrl" not in parsed_data:
            # Only decode snippet for error message if needed (memory efficient)
            xml_snippet = data[:500].decode("utf-8", errors="ignore")
            raise_exception(
                XMLParsingError,
                "Invalid XBRL format",
                "Invalid XBRL format: missing 'xbrl' root element",
                xml_snippet=xml_snippet,
            )

        dict_data = parsed_data["xbrl"]

    except UnicodeDecodeError as e:
        raise_exception(
            XMLParsingError,
            f"Failed to decode XML data: {str(e)}",
            f"Failed to decode XML data: {str(e)}. Data may be corrupted or in wrong encoding.",
        )
    except Exception as e:
        raise_exception(
            XMLParsingError,
            f"Failed to parse XML/XBRL data: {str(e)}",
            f"Failed to parse XML/XBRL data: {str(e)}",
            xml_snippet=data[:500].decode("utf-8", errors="ignore") if data else None,
        )

    # Memory-optimized: use generator expressions and avoid intermediate lists
    cc_keys = (key for key in dict_data.keys() if "cc:" in key)
    uc_keys = (key for key in dict_data.keys() if "uc:" in key)

    # Process items efficiently and build result with single dict construction
    ret_data = []
    for key in chain(cc_keys, uc_keys):
        processed_items = _process_xbrl_item(key, dict_data[key], output_date_format)
        if processed_items:  # Only process if not None/empty
            # Handle both single items and lists
            items_to_process = (
                processed_items
                if isinstance(processed_items, list)
                else [processed_items]
            )

            for row in items_to_process:
                if row:  # Skip None/empty rows
                    data_type = row.get("data_type")
                    value = row.get("value")

                    # Build dict efficiently in single operation - avoid multiple update() calls
                    # Use numpy types for consistent data type handling throughout pipeline
                    new_dict = {
                        "mdrm": row["mdrm"],
                        "rssd": row["rssd"],
                        "quarter": row["quarter"],
                        "data_type": data_type,
                        # Set data fields based on type - use different null values for SOAP vs REST
                        "int_data": (
                            np.int64(value)
                            if data_type == "int" and value is not None
                            else (pd.NA if use_rest_nulls else np.nan)
                        ),
                        "float_data": (
                            np.float64(value)
                            if data_type == "float"
                            else (pd.NA if use_rest_nulls else np.nan)
                        ),
                        "bool_data": (
                            np.bool_(value)
                            if data_type == "bool"
                            else (pd.NA if use_rest_nulls else np.nan)
                        ),
                        "str_data": str(value) if data_type == "str" else None,
                    }
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


def _process_xbrl_item(
    name: str, items: Union[Dict[str, Any], List[Dict[str, Any]]], date_format: str
) -> List[Dict[str, Any]]:
    # incoming is a data dictionary
    results = []
    if not isinstance(items, list):
        items = [items]
    for j, item in enumerate(items):
        context = item.get("@contextRef")
        unit_type = item.get("@unitRef")
        value = item.get("#text")
        mdrm = name.replace("cc:", "").replace("uc:", "")

        if context is None:
            continue  # Skip items without context

        rssd = context.split("_")[1]
        # date = int(context.split('_')[2].replace("-",''))

        matches = re_date.findall(context)
        if not matches:
            continue  # Skip items without valid date
        quarter = matches[0]

        # transform the date to the requested date format
        if date_format == "string_original":
            quarter = _create_ffiec_date_from_datetime(
                datetime.strptime(quarter, "%Y-%m-%d")
            )
        elif date_format == "string_yyyymmdd":
            quarter = datetime.strptime(quarter, "%Y-%m-%d").strftime("%Y%m%d")
        elif date_format == "python_format":
            quarter = datetime.strptime(quarter, "%Y-%m-%d")

        data_type = None

        if unit_type == "USD" and value is not None:
            value = int(value) // 1000  # Use integer division to keep result as int
            data_type = "int"
        elif unit_type == "PURE" and value is not None:
            value = float(value)
            data_type = "float"
        elif unit_type == "NON-MONETARY" and value is not None:
            value = float(value)
            data_type = "float"
        elif value == "true":
            value = True
            data_type = "bool"
        elif value == "false":
            value = False
            data_type = "bool"
        else:
            data_type = "str"

        results.append(
            {
                "mdrm": mdrm,
                "rssd": rssd,  # Institution RSSD ID
                "id_rssd": rssd,  # Institution RSSD ID (same data, dual field support)
                "value": value,
                "data_type": data_type,
                "quarter": quarter,
            }
        )

    return results
