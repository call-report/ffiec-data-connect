#!/usr/bin/env python3
"""Debug the exact REST query being made for UBPR data."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials
from ffiec_data_connect.protocol_adapter import RESTAdapter

def debug_rest_query():
    """Debug the exact REST query being made for UBPR data."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("DEBUG: REST QUERY FOR UBPR DATA")
    print("=" * 50)
    
    RSSD_ID = "852218"
    REPORTING_PERIOD = "2023-12-31"
    
    # Create REST adapter directly
    adapter = RESTAdapter(rest_credentials)
    
    print("REST QUERY DETAILS:")
    print(f"Base URL: {adapter.BASE_URL}")
    print(f"Endpoint: RetrieveFacsimile")
    print(f"Full URL: {adapter.BASE_URL}/RetrieveFacsimile")
    print()
    
    # Show headers that will be sent
    auth_headers = rest_credentials.get_auth_headers()
    print("AUTHENTICATION HEADERS:")
    for key, value in auth_headers.items():
        if key.lower() == 'authentication':
            print(f"  {key}: [Bearer token - {len(value)} chars]")
        else:
            print(f"  {key}: {value}")
    print()
    
    # Show additional headers for UBPR
    series_mapped = "Call" if "call" == "call" else "UBPR"  # Will be UBPR
    additional_headers = {
        "dataSeries": series_mapped,
        "fiIdType": "ID_RSSD",
        "fiId": str(RSSD_ID),
        "reportingPeriodEndDate": REPORTING_PERIOD,
        "facsimileFormat": "XBRL"
    }
    
    print("ADDITIONAL HEADERS FOR UBPR:")
    for key, value in additional_headers.items():
        print(f"  {key}: {value}")
    print()
    
    print("COMPLETE HTTP REQUEST:")
    print(f"GET {adapter.BASE_URL}/RetrieveFacsimile")
    print("Headers:")
    all_headers = {**auth_headers, **additional_headers}
    for key, value in all_headers.items():
        if key.lower() == 'authentication':
            print(f"  {key}: [Bearer token]")
        else:
            print(f"  {key}: {value}")
    print()
    
    # Now actually make the request and see what happens
    print("MAKING ACTUAL REQUEST...")
    try:
        ubpr_data = fdc.collect_data(
            session=None,
            creds=rest_credentials,
            reporting_period=REPORTING_PERIOD,
            rssd_id=RSSD_ID,
            series="ubpr",
            output_type="list"
        )
        
        print(f"✅ SUCCESS: Retrieved {len(ubpr_data)} UBPR data points")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"Error type: {type(e)}")
        
        # Check if it's our ValidationError
        if hasattr(e, 'details'):
            print(f"Error details: {e.details}")

if __name__ == "__main__":
    debug_rest_query()