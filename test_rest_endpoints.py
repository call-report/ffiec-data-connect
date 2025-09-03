#!/usr/bin/env python3
"""
Test script to verify which FFIEC REST API endpoints are actually working.
"""

import httpx
import json
from datetime import datetime

# Test credentials (replace with your actual credentials)
USERNAME = "cfs111"
TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ."

BASE_URL = "https://ffieccdr.azure-api.us/public"

def get_headers(series="Call", **extra_headers):
    """Get standard headers for REST API requests."""
    headers = {
        "UserId": USERNAME,
        "Authentication": f"Bearer {TOKEN}",
        "dataSeries": series
    }
    # Add any extra headers passed in
    headers.update(extra_headers)
    return headers

def test_endpoint(name, path, headers_params=None, method="GET", series="Call"):
    """Test a single endpoint."""
    print(f"\nTesting: {name}")
    print(f"  Endpoint: {method} {path}")
    
    # Get headers with any additional parameters
    headers = get_headers(series, **(headers_params or {}))
    
    url = f"{BASE_URL}/{path}"
    print(f"  Headers: {headers}")
    print(f"  Full URL: {url}")
    
    try:
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, headers=headers, timeout=30)
            else:
                # For POST, send params as JSON body if needed
                response = client.post(url, headers=headers, json=headers_params, timeout=30)
            
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
    print("=" * 60)
    
    # Test 1: RetrieveReportingPeriods (KNOWN WORKING)
    test_endpoint(
        "RetrieveReportingPeriods",
        "RetrieveReportingPeriods"
    )
    
    # Test 2: RetrievePanelOfReporters
    test_endpoint(
        "RetrievePanelOfReporters",
        "RetrievePanelOfReporters",
        headers_params={"reportingPeriodEndDate": "12/31/2023"}
    )
    
    # Test 3: RetrieveFilersSinceDate
    test_endpoint(
        "RetrieveFilersSinceDate",
        "RetrieveFilersSinceDate",
        headers_params={
            "reportingPeriodEndDate": "12/31/2023",
            "lastUpdateDateTime": "01/01/2023"  # Use simple date format per PDF
        }
    )
    
    # Test 4: RetrieveFilersSubmissionDateTime
    test_endpoint(
        "RetrieveFilersSubmissionDateTime",
        "RetrieveFilersSubmissionDateTime",
        headers_params={"reportingPeriodEndDate": "12/31/2023"}
    )
    
    # Test 5: RetrieveFacsimile (Individual bank data)
    test_endpoint(
        "RetrieveFacsimile",
        "RetrieveFacsimile",
        headers_params={
            "fiIdType": "ID_RSSD",  # Note: lowercase 'd' in fiId per PDF
            "fiId": "480228",  # JPMorgan Chase
            "reportingPeriodEndDate": "12/31/2023",
            "facsimileFormat": "XBRL"
        }
    )
    
    # Test 6: Try POST version of RetrieveFacsimile (may not exist)
    test_endpoint(
        "RetrieveFacsimileExt (POST)",
        "RetrieveFacsimileExt",
        headers_params={
            "fiIdType": "ID_RSSD",
            "fiId": "480228",
            "reportingPeriodEndDate": "12/31/2023",
            "facsimileFormat": "XBRL"
        },
        method="POST"
    )
    
    # Test 7: RetrieveUBPRXBRLFacsimile
    test_endpoint(
        "RetrieveUBPRXBRLFacsimile",
        "RetrieveUBPRXBRLFacsimile",
        headers_params={
            "fiIdType": "ID_RSSD",
            "fiId": "480228",
            "reportingPeriodEndDate": "12/31/2023"
        },
        series="UBPR"  # Uppercase per PDF
    )
    
    print("\n" + "=" * 60)
    print("Testing Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()