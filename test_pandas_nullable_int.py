#!/usr/bin/env python3
"""Test pandas nullable integer approach."""

import pandas as pd
import numpy as np

def test_nullable_int():
    """Test different approaches to handle integers with missing values in pandas."""
    
    print("TEST: Pandas Nullable Integer Approaches")
    print("=" * 50)
    
    # Sample data similar to FFIEC structure
    data = [
        {'data_type': 'int', 'int_data': np.int64(30526000), 'float_data': None},
        {'data_type': 'float', 'int_data': None, 'float_data': 123.45},
        {'data_type': 'int', 'int_data': np.int64(540000), 'float_data': None},
        {'data_type': 'float', 'int_data': None, 'float_data': 67.89}
    ]
    
    print("1. Standard DataFrame (current approach):")
    df1 = pd.DataFrame(data)
    print(f"   Dtypes: {df1.dtypes}")
    print(f"   int_data values: {df1['int_data'].values}")
    print()
    
    print("2. Using pd.NA for missing values:")
    data_with_pd_na = [
        {'data_type': 'int', 'int_data': np.int64(30526000), 'float_data': pd.NA},
        {'data_type': 'float', 'int_data': pd.NA, 'float_data': 123.45},
        {'data_type': 'int', 'int_data': np.int64(540000), 'float_data': pd.NA},
        {'data_type': 'float', 'int_data': pd.NA, 'float_data': 67.89}
    ]
    
    df2 = pd.DataFrame(data_with_pd_na)
    # Convert to nullable integer
    df2['int_data'] = df2['int_data'].astype('Int64')  # Capital I for nullable
    print(f"   Dtypes: {df2.dtypes}")
    print(f"   int_data values: {df2['int_data'].values}")
    print()
    
    print("3. Separate the data by type (like separate tables):")
    # This would be the approach used in notebooks
    int_only = df1[df1['data_type'] == 'int'][['data_type', 'int_data']]
    print(f"   Integer-only data dtypes: {int_only.dtypes}")
    print(f"   Integer-only values: {int_only['int_data'].values}")

if __name__ == "__main__":
    test_nullable_int()