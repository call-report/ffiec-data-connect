#!/usr/bin/env python3
"""
Test the REST adapter implementation to ensure it correctly uses the REST API endpoints.
"""

import sys
sys.path.insert(0, 'src')

from ffiec_data_connect.credentials import OAuth2Credentials
from ffiec_data_connect.protocol_adapter import RESTAdapter
import json

# Test credentials
USERNAME = "cfs111"
TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ."

def test_rest_adapter():
    """Test REST adapter methods."""
    print("=" * 60)
    print("Testing REST Adapter Implementation")
    print("=" * 60)
    
    # Create credentials and adapter
    creds = OAuth2Credentials(username=USERNAME, bearer_token=TOKEN)
    adapter = RESTAdapter(creds)
    
    # Test 1: RetrieveReportingPeriods
    print("\n1. Testing retrieve_reporting_periods (Call series)...")
    try:
        periods = adapter.retrieve_reporting_periods("call")
        print(f"   ✅ SUCCESS: Retrieved {len(periods)} reporting periods")
        if periods:
            print(f"   Latest period: {periods[0]}")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 2: RetrievePanelOfReporters
    print("\n2. Testing retrieve_panel_of_reporters...")
    try:
        reporters = adapter.retrieve_panel_of_reporters("12/31/2023")
        print(f"   ✅ SUCCESS: Retrieved {len(reporters)} reporters")
        if reporters:
            print(f"   Sample reporter: {reporters[0].get('Name', 'N/A')}")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 3: RetrieveFilersSinceDate
    print("\n3. Testing retrieve_filers_since_date...")
    try:
        filers = adapter.retrieve_filers_since_date("12/31/2023", "01/01/2023")
        print(f"   ✅ SUCCESS: Retrieved {len(filers)} filers")
        if filers:
            print(f"   Sample RSSD: {filers[0]}")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 4: RetrieveFilersSubmissionDateTime
    print("\n4. Testing retrieve_filers_submission_datetime...")
    try:
        submissions = adapter.retrieve_filers_submission_datetime("12/31/2023")
        print(f"   ✅ SUCCESS: Retrieved {len(submissions)} submissions")
        if submissions:
            print(f"   Sample submission: RSSD {submissions[0].get('ID_RSSD', 'N/A')}")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 5: RetrieveFacsimile
    print("\n5. Testing retrieve_facsimile...")
    try:
        facsimile = adapter.retrieve_facsimile("480228", "12/31/2023", "call")
        print(f"   ✅ SUCCESS: Retrieved facsimile ({len(facsimile)} bytes)")
        # Check if it's valid XBRL (starts with <?xml)
        if facsimile[:5] == b'<?xml':
            print(f"   Valid XBRL document detected")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 6: RetrieveUBPRReportingPeriods
    print("\n6. Testing retrieve_ubpr_reporting_periods...")
    try:
        ubpr_periods = adapter.retrieve_ubpr_reporting_periods()
        print(f"   ✅ SUCCESS: Retrieved {len(ubpr_periods)} UBPR periods")
        if ubpr_periods:
            print(f"   Latest UBPR period: {ubpr_periods[0]}")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    # Test 7: RetrieveUBPRXBRLFacsimile
    print("\n7. Testing retrieve_ubpr_xbrl_facsimile...")
    try:
        ubpr_xbrl = adapter.retrieve_ubpr_xbrl_facsimile("480228", "12/31/2023")
        print(f"   ✅ SUCCESS: Retrieved UBPR XBRL ({len(ubpr_xbrl)} bytes)")
        # Check if it's valid XBRL
        if ubpr_xbrl[:5] == b'<?xml':
            print(f"   Valid XBRL document detected")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
    
    print("\n" + "=" * 60)
    print("REST Adapter Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_rest_adapter()