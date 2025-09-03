#!/usr/bin/env python3
"""Test UBPR data collection for RSSD 37."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_ubpr_rssd_37():
    """Test UBPR data collection for RSSD 37."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("TEST: UBPR Data Collection for RSSD 37")
    print("=" * 50)
    
    RSSD_ID = "37"
    
    # First check available periods
    print("1. Checking available UBPR periods...")
    try:
        ubpr_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="ubpr",
            output_type="list"
        )
        
        print(f"✅ Found {len(ubpr_periods)} UBPR periods")
        print(f"Recent periods: {ubpr_periods[:5]}")
        print(f"Older periods: {ubpr_periods[-5:]}")
        
        # Test with multiple periods
        test_periods = []
        if len(ubpr_periods) >= 1:
            test_periods.append(ubpr_periods[0])  # Most recent
        if len(ubpr_periods) >= 5:
            test_periods.append(ubpr_periods[4])  # 5th most recent
        if len(ubpr_periods) >= 10:
            test_periods.append(ubpr_periods[9])  # 10th most recent
        
        for i, test_period in enumerate(test_periods, 2):
            print(f"\n{i}. Testing UBPR data for RSSD {RSSD_ID}, period {test_period}")
            
            try:
                ubpr_data = fdc.collect_data(
                    session=None,
                    creds=rest_credentials,
                    reporting_period=test_period,
                    rssd_id=RSSD_ID,
                    series="ubpr",
                    output_type="list"
                )
                
                print(f"✅ SUCCESS: Retrieved {len(ubpr_data)} UBPR data points for {test_period}")
                if ubpr_data:
                    print(f"   Sample item: {ubpr_data[0]}")
                
            except Exception as e:
                print(f"❌ ERROR with {test_period}: {e}")
                print(f"   Error type: {type(e)}")
        
    except Exception as e:
        print(f"❌ Error getting UBPR periods: {e}")
        print(f"   Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ubpr_rssd_37()