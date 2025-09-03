#!/usr/bin/env python3
"""Test how integer data displays in DataFrames."""

import os
import sys
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ffiec_data_connect as fdc
from ffiec_data_connect import OAuth2Credentials
import pandas as pd

def test_integer_display():
    """Test how integer data displays in DataFrames."""
    
    # User's credentials
    rest_credentials = OAuth2Credentials(
        username="cfs111",
        bearer_token="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ.",
        token_expires=datetime.now() + timedelta(days=90)
    )
    
    print("TEST: Integer Display in DataFrames")
    print("=" * 40)
    
    RSSD_ID = "852218"
    
    # Get Call Report data
    try:
        call_periods = fdc.collect_reporting_periods(
            session=None,
            creds=rest_credentials,
            series="call",
            output_type="list"
        )
        
        test_period = call_periods[-1]  # Most recent
        print(f"Testing with period: {test_period}")
        
        call_data = fdc.collect_data(
            session=None,
            creds=rest_credentials,
            reporting_period=test_period,
            rssd_id=RSSD_ID,
            series="call",
            output_type="list"
        )
        
        print(f"\n1. Raw data sample:")
        sample_item = call_data[0]
        print(f"   {sample_item}")
        print(f"   int_data type: {type(sample_item['int_data'])}")
        print(f"   int_data value: {sample_item['int_data']}")
        
        # Test with DataFrame
        print(f"\n2. DataFrame display:")
        df = pd.DataFrame(call_data)
        
        # Show data types
        print("DataFrame dtypes:")
        print(df.dtypes)
        
        # Show first few integer rows
        int_rows = df[df['data_type'] == 'int'].head(3)
        print(f"\nFirst 3 integer data rows:")
        print(int_rows[['mdrm', 'int_data', 'data_type']])
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integer_display()