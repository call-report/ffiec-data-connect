"""Internal functions to assist with processing results from the Webservice
"""


from zeep import helpers

def _normalize_output_from_reporter_panel(row: dict) -> dict:

    """Normalize the output from the reporter panel into a dict
    Converts integers to strings,
    for zipcode, convert to string and zfill for 5 digits
    change hasFiledForReportingPeriod to bool,
    and change all field names to camel case

    Returns:
        _type_: _description_
    """



    new_row = {}
    row_keys = list(helpers.serialize_object(row).keys())
    
    # process ID_RSSD
    if 'ID_RSSD' in row_keys:
        new_row['id_rssd'] = str(row['ID_RSSD'])
    else:
        new_row['id_rssd'] = None

    # process FDIC CERT NUMBER
    if 'FDICCertNumber' in row_keys:
        if row['FDICCertNumber'] != 0:
            new_row['fdic_cert_number'] = str(row['FDICCertNumber'])
        else:
            new_row['fdic_cert_number'] = None
    else:
        new_row["fdic_cert_number" ] = None
        
    # OCC chart number
    if 'OCCChartNumber' in row_keys:
        if row['OCCChartNumber'] != 0:
            new_row['occ_chart_number'] = str(row['OCCChartNumber'])
        else:
            new_row['occ_chart_number'] = None
    else: 
        new_row['occ_chart_number'] = None
        
    # process OTSDockNumber
    if 'OTSDockNumber' in row_keys:
        if row['OTSDockNumber'] != 0:
            new_row['ots_dock_number'] = str(row['OTSDockNumber'])
        else:
            new_row['ots_dock_number'] = None
    else:
        new_row['ots_dock_number'] = None
        
    # process PrimaryABARoutNumber
    if 'PrimaryABARoutNumber' in row_keys:
        if row['PrimaryABARoutNumber'] != 0:
            new_row['primary_aba_rout_number'] = str(row['PrimaryABARoutNumber'])
        else:
            new_row['primary_aba_rout_number'] = None
    
    # Process Name
    if 'Name' in row_keys:
        temp_str = row['Name'].strip()
        if temp_str == '0' or temp_str == '':
            new_row['name'] = temp_str
        else:
            new_row['name'] = temp_str
       
    else:
        new_row['name'] = None
    
    #Process State
    if 'State' in row_keys:
        temp_str = row['State'].strip()
        if temp_str == '0' or temp_str == '':
            new_row['state'] = temp_str
        else:
            new_row['state'] = temp_str
    else:
        new_row['city'] = None
    
    # Process City
    if 'City' in row_keys:
        temp_str = row['City'].strip()
        if temp_str == '0' or temp_str == '':
            new_row['city'] = temp_str
        else:
            new_row['city'] = temp_str        
    else:
        new_row['city'] = None

    
    # Process Address
    if 'Address' in row_keys:
        temp_str = row['Address'].strip()
        if temp_str == '0' or temp_str == '':
            new_row['address'] = temp_str
        else:
            new_row['address'] = temp_str
            

    #Process Zip
    if 'Zip' in row_keys:
        temp_str = str(row['Zip']).zfill(5)
        if temp_str == '0' or temp_str == '':
            new_row['zip'] = temp_str
        else:
            new_row['zip'] = temp_str
            
    
    #Process FilingType
    if 'FilingType' in row_keys:
        temp_str = row['FilingType'].strip()
        if temp_str == '0' or temp_str == '':
            new_row['filing_type'] = temp_str
        else:
            new_row['filing_type'] = temp_str
            
    # process HasFiledForReportingPeriod
    if 'HasFiledForReportingPeriod' in row_keys:
        if type(row['HasFiledForReportingPeriod']) == bool:
            new_row['has_filed_for_reporting_period'] = row['HasFiledForReportingPeriod']
        else:
            new_row['has_filed_for_reporting_period'] = None
            

    return new_row
    
    