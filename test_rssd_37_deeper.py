#!/usr/bin/env python3
"""Check RSSD 37 in older periods and available series."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_rssd_37_deeper():
    """Check RSSD 37 in older periods and available series."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("DEEPER INVESTIGATION: RSSD 37")
    print("=" * 50)
    
    RSSD_ID = "37"
    
    # Check multiple older periods for filers
    older_periods = ["2020-12-31", "2015-12-31", "2010-12-31", "2005-12-31"]
    
    for period in older_periods:
        print(f"\n1. Checking filers for period {period}...")
        try:
            filers = fdc.collect_filers_on_reporting_period(
                session=None,
                creds=rest_credentials,
                reporting_period=period,
                output_type="list"
            )
            
            # Look for RSSD 37
            rssd_37_info = None
            for filer in filers:
                if str(filer.get('rssd', '')) == RSSD_ID:
                    rssd_37_info = filer
                    break
            
            if rssd_37_info:
                print(f"✅ FOUND RSSD 37 in {period}:")
                print(f"   Name: {rssd_37_info.get('name', 'N/A')}")
                print(f"   City: {rssd_37_info.get('city', 'N/A')}")
                print(f"   State: {rssd_37_info.get('state', 'N/A')}")
                
                # Now try UBPR for this period
                print(f"\n   Testing UBPR data for {period}...")
                try:
                    ubpr_data = fdc.collect_data(
                        session=None,
                        creds=rest_credentials,
                        reporting_period=period,
                        rssd_id=RSSD_ID,
                        series="ubpr",
                        output_type="list"
                    )
                    
                    print(f"   ✅ UBPR SUCCESS: Retrieved {len(ubpr_data)} data points")
                    if ubpr_data:
                        print(f"      Sample: {ubpr_data[0]}")
                        
                except Exception as e:
                    print(f"   ❌ UBPR ERROR: {e}")
                
                break  # Found it, no need to check other periods
            else:
                print(f"❌ RSSD 37 not found in {period} (total filers: {len(filers)})")
        
        except Exception as e:
            print(f"❌ Error checking period {period}: {e}")
    
    # Let's also check what the first few RSSD IDs are to understand the pattern
    print(f"\n2. Sample of lowest RSSD IDs in recent period...")
    try:
        filers = fdc.collect_filers_on_reporting_period(
            session=None,
            creds=rest_credentials,
            reporting_period="2024-06-30",
            output_type="list"
        )
        
        # Sort by RSSD ID to see the lowest ones
        sorted_filers = sorted(filers, key=lambda x: int(x.get('rssd', 999999)))
        
        print("Lowest 10 RSSD IDs:")
        for i, filer in enumerate(sorted_filers[:10]):
            print(f"   RSSD {filer.get('rssd')}: {filer.get('name', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error getting sample RSSSDs: {e}")

if __name__ == "__main__":
    test_rssd_37_deeper()