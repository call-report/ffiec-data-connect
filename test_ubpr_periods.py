#!/usr/bin/env python3
"""Check what UBPR periods are available."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_ubpr_periods():
    """Check what UBPR periods are available."""
    
    # Real credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("UBPR PERIODS AND DATA AVAILABILITY TEST")
    print("=" * 60)
    
    # Check UBPR periods
    print("1. Checking available UBPR periods...")
    try:
        ubpr_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="ubpr",
            output_type="list"
        )
        
        print(f"✅ Found {len(ubpr_periods)} UBPR periods")
        print(f"Recent UBPR periods: {ubpr_periods[:10]}")
        print(f"Oldest UBPR periods: {ubpr_periods[-5:]}")
        
        # Test with older UBPR period
        if ubpr_periods:
            test_period = ubpr_periods[10] if len(ubpr_periods) > 10 else ubpr_periods[-1]
            print(f"\n2. Testing UBPR data for period: {test_period}")
            
            try:
                ubpr_data = fdc.collect_data(
                    session=None,
                    creds=rest_credentials,
                    reporting_period=test_period,
                    rssd_id="480228",
                    series="ubpr",
                    output_type="list"
                )
                
                print(f"✅ SUCCESS: Retrieved {len(ubpr_data)} UBPR data points for {test_period}")
                if ubpr_data:
                    print(f"   Sample item: {ubpr_data[0]}")
                    
            except Exception as e:
                print(f"❌ ERROR with {test_period}: {e}")
                
                # Try with an even older period
                if len(ubpr_periods) > 20:
                    older_period = ubpr_periods[-10]
                    print(f"\n3. Trying older UBPR period: {older_period}")
                    
                    try:
                        ubpr_data = fdc.collect_data(
                            session=None,
                            creds=rest_credentials,
                            reporting_period=older_period,
                            rssd_id="480228", 
                            series="ubpr",
                            output_type="list"
                        )
                        
                        print(f"✅ SUCCESS: Retrieved {len(ubpr_data)} UBPR data points for {older_period}")
                        
                    except Exception as e2:
                        print(f"❌ ERROR with {older_period}: {e2}")
                        print("\n⚠️ UBPR data may not be available via REST API yet")
        
    except Exception as e:
        print(f"❌ Error getting UBPR periods: {e}")

if __name__ == "__main__":
    test_ubpr_periods()