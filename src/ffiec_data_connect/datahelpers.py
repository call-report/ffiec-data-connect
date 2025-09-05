"""Internal functions to assist with processing results from the Webservice"""

from typing import Any, Dict, Optional, Union

from zeep import helpers


def _normalize_output_from_reporter_panel(
    row: Dict[str, Any],
) -> Dict[str, Optional[Union[str, bool]]]:
    """Normalize the output from the reporter panel into a dict
    Converts integers to strings,
    for zipcode, convert to string and zfill for 5 digits
    change hasFiledForReportingPeriod to bool,
    and change all field names to camel case

    Returns:
        _type_: _description_
    """

    new_row: Dict[str, Optional[Union[str, bool]]] = {}
    row_keys = list(helpers.serialize_object(row).keys())  # type: ignore[no-untyped-call]

    # process ID_RSSD - provide both field names for compatibility
    # NOTE: Property names were inconsistent in earlier code, so we provide both
    # 'rssd' and 'id_rssd' to reduce need to refactor existing user code
    if "ID_RSSD" in row_keys:
        rssd_value = str(row["ID_RSSD"])
        new_row["id_rssd"] = rssd_value  # Institution RSSD ID
        new_row["rssd"] = rssd_value  # Institution RSSD ID (same data)
    else:
        new_row["id_rssd"] = None
        new_row["rssd"] = None

    # process FDIC CERT NUMBER
    if "FDICCertNumber" in row_keys:
        if row["FDICCertNumber"] != 0:
            new_row["fdic_cert_number"] = str(row["FDICCertNumber"])
        else:
            new_row["fdic_cert_number"] = None
    else:
        new_row["fdic_cert_number"] = None

    # OCC chart number
    if "OCCChartNumber" in row_keys:
        if row["OCCChartNumber"] != 0:
            new_row["occ_chart_number"] = str(row["OCCChartNumber"])
        else:
            new_row["occ_chart_number"] = None
    else:
        new_row["occ_chart_number"] = None

    # process OTSDockNumber
    if "OTSDockNumber" in row_keys:
        if row["OTSDockNumber"] != 0:
            new_row["ots_dock_number"] = str(row["OTSDockNumber"])
        else:
            new_row["ots_dock_number"] = None
    else:
        new_row["ots_dock_number"] = None

    # process PrimaryABARoutNumber
    if "PrimaryABARoutNumber" in row_keys:
        if row["PrimaryABARoutNumber"] != 0:
            new_row["primary_aba_rout_number"] = str(row["PrimaryABARoutNumber"])
        else:
            new_row["primary_aba_rout_number"] = None

    # Process Name
    if "Name" in row_keys:
        temp_str = row["Name"].strip()
        if temp_str == "0" or temp_str == "":
            new_row["name"] = temp_str
        else:
            new_row["name"] = temp_str

    else:
        new_row["name"] = None

    # Process State
    if "State" in row_keys:
        temp_str = row["State"].strip()
        if temp_str == "0" or temp_str == "":
            new_row["state"] = temp_str
        else:
            new_row["state"] = temp_str
    else:
        new_row["city"] = None

    # Process City
    if "City" in row_keys:
        temp_str = row["City"].strip()
        if temp_str == "0" or temp_str == "":
            new_row["city"] = temp_str
        else:
            new_row["city"] = temp_str
    else:
        new_row["city"] = None

    # Process Address
    if "Address" in row_keys:
        temp_str = row["Address"].strip()
        if temp_str == "0" or temp_str == "":
            new_row["address"] = temp_str
        else:
            new_row["address"] = temp_str

    # Process Zip (handle both "Zip" and "ZIP" for REST API compatibility)
    zip_field = None
    if "Zip" in row_keys:
        zip_field = "Zip"
    elif "ZIP" in row_keys:
        zip_field = "ZIP"

    if zip_field:
        temp_str = str(row[zip_field]).zfill(5)
        if temp_str == "0" or temp_str == "":
            new_row["zip"] = temp_str
        else:
            new_row["zip"] = temp_str
    else:
        new_row["zip"] = None

    # Process FilingType
    if "FilingType" in row_keys:
        temp_str = row["FilingType"].strip()
        if temp_str == "0" or temp_str == "":
            new_row["filing_type"] = temp_str
        else:
            new_row["filing_type"] = temp_str

    # process HasFiledForReportingPeriod
    if "HasFiledForReportingPeriod" in row_keys:
        if isinstance(row["HasFiledForReportingPeriod"], bool):
            new_row["has_filed_for_reporting_period"] = row[
                "HasFiledForReportingPeriod"
            ]
        else:
            new_row["has_filed_for_reporting_period"] = None

    return new_row
