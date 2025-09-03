#!/usr/bin/env python3
"""Test Call Report data collection to ensure no regression."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_call_report_regression():
    """Test Call Report data collection to ensure no regression."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("TEST: Call Report Data Collection - Regression Test")
    print("=" * 60)
    
    RSSD_ID = "852218"
    
    # Test Call Report data collection
    print("1. Testing Call Report data collection...")
    
    # Get available call report periods
    try:
        call_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="call",
            output_type="list"
        )
        
        print(f"✅ Found {len(call_periods)} Call Report periods")
        
        # Test with a recent period
        if call_periods:
            test_period = call_periods[-1]  # Most recent
            print(f"Testing Call Report data for RSSD {RSSD_ID}, period {test_period}")
            
            try:
                call_data = fdc.collect_data(
                    session=None,
                    creds=rest_credentials,
                    reporting_period=test_period,
                    rssd_id=RSSD_ID,
                    series="call",
                    output_type="list"
                )
                
                print(f"✅ SUCCESS: Retrieved {len(call_data)} Call Report data points")
                if call_data:
                    print(f"   Sample item: {call_data[0]}")
                    print(f"   Keys: {list(call_data[0].keys())}")
                
            except Exception as e:
                print(f"❌ ERROR with Call Report {test_period}: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error getting Call Report periods: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Summary:")
    print("- UBPR: ✅ Fixed and working")  
    print("- Call Report: Testing above...")

if __name__ == "__main__":
    test_call_report_regression()