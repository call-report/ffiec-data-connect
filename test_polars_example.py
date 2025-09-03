#!/usr/bin/env python3
"""Test Polars DataFrame display with FFIEC data."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials

def test_polars_example():
    """Test Polars DataFrame display with FFIEC data."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("POLARS DATAFRAME EXAMPLE")
    print("=" * 40)
    
    RSSD_ID = "852218"
    PERIOD = "2024-06-30"
    
    try:
        # Get Call Report data as Polars DataFrame
        print("⚡ Getting data as Polars DataFrame...")
        
        call_data_polars = fdc.collect_data(
            session=None,
            creds=rest_credentials,
            reporting_period=PERIOD,
            rssd_id=RSSD_ID,
            series="call",
            output_type="polars"
        )
        
        print(f"Polars DataFrame shape: {call_data_polars.shape}")
        print("Schema (first 10 columns):")
        for name, dtype in list(call_data_polars.schema.items())[:10]:
            print(f"  {name}: {dtype}")
        
        print()
        
        # Filter for integer data to show the example
        int_data = call_data_polars.filter(
            call_data_polars["data_type"] == "int"
        ).head(5)
        
        print("📊 Sample integer data (first 5 rows):")
        print(int_data.select(["mdrm", "int_data", "data_type"]))
        print()
        
        # Get a specific integer value to test
        sample_int_row = int_data.row(0)  # Get first row as tuple
        sample_int_value = sample_int_row[4]  # int_data is 5th column (index 4)
        
        print(f"Sample Integer value: {sample_int_value} (type: {type(sample_int_value)})")
        print()
        
        print("🔍 Checking data format preservation...")
        
        # Check if integers are preserved
        if sample_int_value is not None and not str(sample_int_value).endswith('.0'):
            print("✅ Integer values preserved correctly (no .0 suffix)")
        elif sample_int_value is None:
            print("⚠️ Integer value is None - check data filtering")
        else:
            print(f"❌ Integer showing as: {sample_int_value}")
        
        # Show some float data for comparison
        float_data = call_data_polars.filter(
            call_data_polars["data_type"] == "float"
        ).head(3)
        
        if len(float_data) > 0:
            print("\n📈 Sample float data (for comparison):")
            print(float_data.select(["mdrm", "float_data", "data_type"]))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_polars_example()