#!/usr/bin/env python3
"""Debug the actual UBPR endpoint response."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials
from ffiec_data_connect.protocol_adapter import RESTAdapter

def debug_ubpr_response():
    """Debug the actual UBPR endpoint response."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("DEBUG: UBPR Endpoint Response")
    print("=" * 40)
    
    RSSD_ID = "852218"
    REPORTING_PERIOD = "2023-12-31"
    
    # Create REST adapter directly and call the UBPR method
    adapter = RESTAdapter(rest_credentials)
    
    print(f"Calling RetrieveUBPRXBRLFacsimile endpoint directly...")
    print(f"URL: {adapter.BASE_URL}/RetrieveUBPRXBRLFacsimile")
    print(f"RSSD: {RSSD_ID}, Period: {REPORTING_PERIOD}")
    print()
    
    try:
        # Call the UBPR-specific method directly
        raw_bytes = adapter.retrieve_ubpr_xbrl_facsimile(RSSD_ID, REPORTING_PERIOD)
        
        print(f"✅ Response received: {len(raw_bytes)} bytes")
        print(f"First 200 chars of response:")
        print(repr(raw_bytes[:200]))
        print()
        
        # Try to decode as text to see what it contains
        try:
            text = raw_bytes.decode('utf-8', errors='ignore')
            print(f"Response as text (first 500 chars):")
            print(text[:500])
            print()
            
            if text.strip() == "":
                print("⚠️  Response is empty!")
            elif not text.strip().startswith('<'):
                print("⚠️  Response doesn't start with '<', not XML")
            else:
                print("✅ Response appears to be XML/XBRL")
                
        except Exception as decode_error:
            print(f"❌ Failed to decode as text: {decode_error}")
        
    except Exception as e:
        print(f"❌ ERROR calling UBPR endpoint: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ubpr_response()