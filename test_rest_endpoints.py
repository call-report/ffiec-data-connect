#!/usr/bin/env python3
"""
Test script to verify which FFIEC REST API endpoints are actually working.
Based on official FFIEC document CDR-PDD-SIS-611 v1.10

There are exactly 7 REST endpoints:
1. RetrieveReportingPeriods
2. RetrievePanelOfReporters
3. RetrieveFilersSinceDate
4. RetrieveFilersSubmissionDateTime
5. RetrieveFacsimile
6. RetrieveUBPRReportingPeriods
7. RetrieveUBPRXBRLFacsimile
"""

import httpx
import json
from datetime import datetime

# Test credentials (replace with your actual credentials)
USERNAME = "cfs111"
TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ."

BASE_URL = "https://ffieccdr.azure-api.us/public"

def get_headers(**extra_headers):
    """Get standard headers for REST API requests."""
    headers = {
        "UserID": USERNAME,  # Note capital 'ID' not 'Id'
        "Authentication": f"Bearer {TOKEN}",  # Note: NOT "Authorization"
    }
    # Add any extra headers passed in
    headers.update(extra_headers)
    return headers

def test_endpoint(name, path, headers_params=None, method="GET"):
    """Test a single endpoint."""
    print(f"\nTesting: {name}")
    print(f"  Endpoint: {method} {path}")
    
    # Get headers with any additional parameters
    headers = get_headers(**(headers_params or {}))
    
    url = f"{BASE_URL}/{path}"
    print(f"  Headers: {[k for k in headers.keys()]}")
    print(f"  Full URL: {url}")
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=30)
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                if response.headers.get("content-type", "").startswith("application/json"):
                    data = response.json()
                    if isinstance(data, list):
                        print(f"  ✅ SUCCESS: Returned {len(data)} items")
                        if data and len(data) > 0:
                            print(f"  Sample: {data[0]}")
                    else:
                        print(f"  ✅ SUCCESS: Returned data")
                else:
                    print(f"  ✅ SUCCESS: Returned binary data ({len(response.content)} bytes)")
            else:
                print(f"  ❌ FAILED: {response.status_code}")
                if response.text:
                    print(f"  Response: {response.text[:200]}")
                    
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")

def main():
    print("=" * 60)
    print("FFIEC REST API Endpoint Testing")
    print("Based on CDR-PDD-SIS-611 v1.10")
    print("=" * 60)
    
    # Test 1: RetrieveReportingPeriods (Call series)
    test_endpoint(
        "1. RetrieveReportingPeriods (Call)",
        "RetrieveReportingPeriods",
        headers_params={"dataSeries": "Call"}  # Required header
    )
    
    # Test 2: RetrievePanelOfReporters
    test_endpoint(
        "2. RetrievePanelOfReporters",
        "RetrievePanelOfReporters",
        headers_params={
            "dataSeries": "Call",
            "reportingPeriodEndDate": "12/31/2023"
        }
    )
    
    # Test 3: RetrieveFilersSinceDate
    test_endpoint(
        "3. RetrieveFilersSinceDate",
        "RetrieveFilersSinceDate",
        headers_params={
            "dataSeries": "Call",
            "reportingPeriodEndDate": "12/31/2023",
            "lastUpdateDateTime": "01/01/2023"  # Simple date format
        }
    )
    
    # Test 4: RetrieveFilersSubmissionDateTime
    test_endpoint(
        "4. RetrieveFilersSubmissionDateTime",
        "RetrieveFilersSubmissionDateTime",
        headers_params={
            "dataSeries": "Call",
            "reportingPeriodEndDate": "12/31/2023",
            "lastUpdateDateTime": "01/01/2023"  # Required per PDF
        }
    )
    
    # Test 5: RetrieveFacsimile (Individual bank data)
    test_endpoint(
        "5. RetrieveFacsimile",
        "RetrieveFacsimile",
        headers_params={
            "dataSeries": "Call",
            "reportingPeriodEndDate": "12/31/2023",
            "fiIdType": "ID_RSSD",
            "fiId": "480228",  # JPMorgan Chase
            "facsimileFormat": "XBRL"
        }
    )
    
    # Test 6: RetrieveUBPRReportingPeriods
    # NOTE: This endpoint does NOT require dataSeries header!
    test_endpoint(
        "6. RetrieveUBPRReportingPeriods",
        "RetrieveUBPRReportingPeriods"
        # No dataSeries header needed for UBPR reporting periods
    )
    
    # Test 7: RetrieveUBPRXBRLFacsimile
    # NOTE: This endpoint does NOT require dataSeries header!
    test_endpoint(
        "7. RetrieveUBPRXBRLFacsimile",
        "RetrieveUBPRXBRLFacsimile",
        headers_params={
            # No dataSeries header for UBPR endpoints
            "reportingPeriodEndDate": "12/31/2023",
            "fiIdType": "ID_RSSD",
            "fiId": "480228"
        }
    )
    
    print("\n" + "=" * 60)
    print("Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()