#!/usr/bin/env python3
"""Test UBPR data collection with more recent periods."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_ubpr_recent():
    """Test UBPR data collection with more recent periods."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("TEST: UBPR Data Collection - Recent Periods")
    print("=" * 55)
    
    RSSD_ID = "852218"
    
    # Get available periods and test more recent ones
    try:
        ubpr_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="ubpr",
            output_type="list"
        )
        
        print(f"Found {len(ubpr_periods)} UBPR periods")
        print(f"Most recent: {ubpr_periods[-5:] if len(ubpr_periods) >= 5 else ubpr_periods}")
        print()
        
        # Test with the most recent periods (UBPR periods are stored oldest to newest)
        recent_periods = ubpr_periods[-5:] if len(ubpr_periods) >= 5 else ubpr_periods
        recent_periods.reverse()  # Test newest first
        
        for period in recent_periods[:3]:  # Test top 3 most recent
            print(f"Testing UBPR data for RSSD {RSSD_ID}, period {period}")
            
            try:
                ubpr_data = fdc.collect_data(
                    session=None,
                    creds=rest_credentials,
                    reporting_period=period,
                    rssd_id=RSSD_ID,
                    series="ubpr",
                    output_type="list"
                )
                
                print(f"✅ SUCCESS: Retrieved {len(ubpr_data)} UBPR data points for {period}")
                if ubpr_data:
                    print(f"   Sample item: {ubpr_data[0]}")
                    print(f"   Keys in sample: {list(ubpr_data[0].keys())[:10]}...")
                break  # Success! No need to test more periods
                
            except Exception as e:
                print(f"❌ ERROR with {period}: {e}")
                if "syntax error" in str(e):
                    print("   (XML parsing error - may indicate empty or invalid XBRL)")
                print()
        
    except Exception as e:
        print(f"❌ Error getting UBPR periods: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ubpr_recent()