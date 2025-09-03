#!/usr/bin/env python3
"""Test UBPR with known working RSSD IDs."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_working_ubpr():
    """Test UBPR with known working RSSD IDs."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("TESTING UBPR WITH KNOWN WORKING RSSD IDs")
    print("=" * 60)
    
    # Try some common large bank RSSSDs that should have UBPR
    test_rssd_ids = [
        ("480228", "JPMorgan Chase"),  # This we know failed
        ("451965", "Bank of America"),
        ("213837", "Wells Fargo"),  
        ("12387", "Citibank"),
        ("413208", "Goldman Sachs"),
        ("3511", "PNC Bank"),
        ("541101", "BB&T"),
        ("817824", "SunTrust")
    ]
    
    # Get a recent UBPR period
    try:
        ubpr_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="ubpr",
            output_type="list"
        )
        
        if ubpr_periods:
            # Try a period from 2023 (not too recent, not too old)
            test_period = "2023-12-31"
            if test_period not in ubpr_periods:
                # Use the 10th period if 2023-12-31 isn't available
                test_period = ubpr_periods[min(10, len(ubpr_periods)-1)]
            
            print(f"Testing UBPR period: {test_period}")
            print(f"Available periods: {len(ubpr_periods)}")
            print()
            
            for rssd_id, bank_name in test_rssd_ids:
                print(f"Testing {bank_name} (RSSD: {rssd_id})...")
                
                try:
                    ubpr_data = fdc.collect_data(
                        session=None,
                        creds=rest_credentials,
                        reporting_period=test_period,
                        rssd_id=rssd_id,
                        series="ubpr",
                        output_type="list"
                    )
                    
                    print(f"   ✅ SUCCESS: {len(ubpr_data)} UBPR data points")
                    if ubpr_data:
                        print(f"      Sample: {ubpr_data[0]}")
                    
                except Exception as e:
                    print(f"   ❌ ERROR: {str(e)[:100]}...")
                
                print()
        
        else:
            print("❌ No UBPR periods found")
    
    except Exception as e:
        print(f"❌ Error getting UBPR periods: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_working_ubpr()