#!/usr/bin/env python3
"""Check what institution RSSD 37 is."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_rssd_37_info():
    """Check what institution RSSD 37 is."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("CHECKING RSSD 37 INSTITUTION INFO")
    print("=" * 50)
    
    RSSD_ID = "37"
    
    # Check for CDR data first
    print("1. Testing CDR data availability...")
    try:
        cdr_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="cdr",
            output_type="list"
        )
        
        if cdr_periods:
            test_period = cdr_periods[0]  # Most recent
            print(f"   Testing CDR for period {test_period}")
            
            try:
                cdr_data = fdc.collect_data(
                    session=None,
                    creds=rest_credentials,
                    reporting_period=test_period,
                    rssd_id=RSSD_ID,
                    series="cdr",
                    output_type="list"
                )
                
                print(f"✅ CDR SUCCESS: Retrieved {len(cdr_data)} CDR data points")
                if cdr_data:
                    print(f"   Sample CDR item: {cdr_data[0]}")
                
            except Exception as e:
                print(f"❌ CDR ERROR: {e}")
    
    except Exception as e:
        print(f"❌ Error getting CDR periods: {e}")
    
    # Check institution details via filers
    print("\n2. Checking institution details...")
    try:
        # Get filers for recent period to see institution info
        recent_period = "2024-06-30"
        filers = fdc.collect_filers_on_reporting_period(
            session=None,
            creds=rest_credentials,
            reporting_period=recent_period,
            output_type="list"
        )
        
        # Look for RSSD 37
        rssd_37_info = None
        for filer in filers:
            if str(filer.get('rssd', '')) == RSSD_ID:
                rssd_37_info = filer
                break
        
        if rssd_37_info:
            print(f"✅ Found RSSD 37 institution info:")
            print(f"   Name: {rssd_37_info.get('name', 'N/A')}")
            print(f"   City: {rssd_37_info.get('city', 'N/A')}")
            print(f"   State: {rssd_37_info.get('state', 'N/A')}")
        else:
            print("❌ RSSD 37 not found in recent filers list")
            print(f"   Total filers in {recent_period}: {len(filers)}")
        
    except Exception as e:
        print(f"❌ Error checking filers: {e}")

if __name__ == "__main__":
    test_rssd_37_info()