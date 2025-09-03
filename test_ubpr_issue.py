#!/usr/bin/env python3
"""Test UBPR data collection issue."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_ubpr_issue():
    """Test UBPR data collection to debug the ValidationError."""
    
    # Real credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("TEST: UBPR Data Collection")
    print("=" * 50)
    
    SAMPLE_PERIOD = "2023-12-31"
    RSSD_ID = "480228"  # JPMorgan Chase
    
    print(f"Testing UBPR data for RSSD {RSSD_ID}, period {SAMPLE_PERIOD}")
    
    try:
        ubpr_data = fdc.collect_data(
            session=None,
            creds=rest_credentials,
            reporting_period=SAMPLE_PERIOD,
            rssd_id=RSSD_ID,
            series="ubpr",
            output_type="list"
        )
        
        print(f"✅ SUCCESS: Retrieved {len(ubpr_data)} UBPR data points")
        if ubpr_data:
            print(f"   Sample item: {ubpr_data[0]}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"   Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ubpr_issue()