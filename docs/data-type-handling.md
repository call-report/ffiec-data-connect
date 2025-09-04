# Data Type Handling in FFIEC Data Connect

FFIEC Data Connect provides robust data type handling across multiple protocols (SOAP/REST) and output formats, ensuring data integrity and precision from the original XBRL source through to your final data structure.

## Overview

The library manages data types across three dimensions:

### 1. Protocol Layer (SOAP vs REST)
- **SOAP API**: Original behavior using `np.nan` for nulls (100% backward compatible)
- **REST API**: Enhanced behavior using `pd.NA` for better integer preservation

### 2. Processing Layer
- Automatic XBRL type detection
- Numpy type conversion for consistency
- Protocol-specific null handling

### 3. Output Formats
- **`list`**: Raw Python data types (dict format)
- **`pandas`**: Pandas DataFrames with nullable type support  
- **`polars`**: Polars DataFrames with direct conversion for maximum precision

## Type Conversion Pipeline

### XBRL Source Data

FFIEC webservice returns XBRL (eXtensible Business Reporting Language) documents containing financial data. The library processes these XML documents and determines data types based on XBRL unit attributes:

| XBRL Unit Type | Data Type | Example Value | Description |
|----------------|-----------|---------------|-------------|
| `USD` | Integer | `1500000` | Monetary values (converted from thousands) |
| `PURE` | Float | `1.25` | Ratios and percentages |
| `NON-MONETARY` | Float | `12.5` | Non-monetary numeric values |
| `true`/`false` | Boolean | `True`/`False` | Boolean indicators |
| Other | String | `"N/A"` | Text values |

### Internal Processing

The XBRL processor (`xbrl_processor.py`) converts XBRL values to numpy types for consistent handling:

```python
# Internal data structure uses numpy types
{
    'mdrm': 'RCON2170',           # MDRM code (string)
    'rssd': '480228',             # RSSD ID (string) 
    'id_rssd': '480228',          # RSSD ID (same data, dual field support)
    'quarter': '2023-12-31',      # Reporting period (string)
    'data_type': 'int',           # Detected type
    'int_data': np.int64(1500000),    # Integer data (or np.nan)
    'float_data': np.nan,             # Float data (or value)
    'bool_data': np.nan,              # Boolean data (or value)
    'str_data': None                  # String data (or value)
}
```

**Key Design Principles:**
- Only one data field contains the actual value; others are `np.nan` or `None`
- Preserves original precision from XBRL source
- Uses numpy types for consistent downstream processing
- Provides dual field names (`rssd` and `id_rssd`) for backward compatibility

## Field Name Compatibility

**Important**: Property names were inconsistent in earlier versions of this library. To reduce the need to refactor existing user code, all functions that return RSSD data now provide **both field names** with identical data:

- `"rssd"`: Institution RSSD ID
- `"id_rssd"`: Institution RSSD ID (same data, different field name)

### Usage Examples

```python
# Both of these work identically:
rssd_id = data_record.get("rssd")      
rssd_id = data_record.get("id_rssd")   

# Defensive programming (recommended for production):
rssd_id = data_record.get("rssd") or data_record.get("id_rssd")
```

### Affected Functions and Data Structures

This dual field name support applies to:
- `collect_filers_on_reporting_period()`
- `collect_filers_submission_date_time()` 
- `collect_data()` (via XBRL processor)
- All REST and SOAP implementations
- All output formats (list, pandas, polars)

## Output Format Details

### List Output (`output_type="list"`)

Returns raw Python dictionaries with numpy types preserved.

```python
data = collect_data(..., output_type="list")
# Returns: List[Dict[str, Any]]

# Example record:
{
    'mdrm': 'RCON2170',
    'rssd': '480228', 
    'quarter': '2023-12-31',
    'data_type': 'int',
    'int_data': numpy.int64(1500000),
    'float_data': nan,
    'bool_data': nan,
    'str_data': None
}
```

**Use Cases:**
- Raw data processing
- Custom data transformations
- Integration with other data processing libraries

### Pandas Output (`output_type="pandas"`)

Creates pandas DataFrames with nullable types to preserve integer precision and handle missing values correctly.

```python
import pandas as pd

df = collect_data(..., output_type="pandas")
# Returns: pandas.DataFrame

# DataFrame dtypes:
# int_data      Int64      # Nullable integer (preserves integers)
# float_data    float64    # Standard float (supports NaN)
# bool_data     boolean    # Nullable boolean
# str_data      string     # Pandas string type
```

**Type Conversion Process:**
1. Create DataFrame from processed XBRL data
2. Apply nullable pandas types:
   - `'Int64'` for integer data (supports `pd.NA`)
   - `'float64'` for float data (supports `np.nan`)
   - `'boolean'` for boolean data (supports `pd.NA`)
   - `'string'` for string data (supports `pd.NA`)

**Benefits:**
- Integers display as integers (not `float64`)
- Proper null handling with `pd.NA`
- Compatible with pandas ecosystem
- Maintains data type semantics

**Example:**
```python
print(df['int_data'].dtype)  # Int64
print(df['int_data'].iloc[0])  # 1500000 (not 1500000.0)
```

### Polars Output (`output_type="polars"`)

Direct conversion from XBRL data to polars DataFrames, bypassing pandas entirely for maximum precision preservation.

```python
import polars as pl

df = collect_data(..., output_type="polars") 
# Returns: polars.DataFrame

# DataFrame schema:
# int_data      Int64      # Native polars integer
# float_data    Float64    # Native polars float
# bool_data     Boolean    # Native polars boolean  
# str_data      Utf8       # Native polars string
```

**Direct Conversion Process:**
1. Process XBRL data with numpy types
2. Convert numpy types to native Python types:
   - `np.int64(value)` → `int(value)`
   - `np.float64(value)` → `float(value)`
   - `np.bool_(value)` → `bool(value)`
   - `np.nan` → `None` (polars null)
3. Create polars DataFrame with explicit schema

**Maximum Precision Benefits:**
- **No intermediate pandas conversion** - eliminates potential precision loss
- **Direct numpy → polars mapping** - preserves exact values
- **Explicit schema enforcement** - guarantees consistent types
- **Optimized memory usage** - no redundant conversions

**Schema Definition:**
```python
schema = {
    'mdrm': pl.Utf8,
    'rssd': pl.Utf8, 
    'quarter': pl.Utf8,
    'data_type': pl.Utf8,
    'int_data': pl.Int64,     # Preserves integer precision
    'float_data': pl.Float64,  # Native float precision
    'bool_data': pl.Boolean,   # True boolean type
    'str_data': pl.Utf8        # String type
}
```

## Null Handling Strategy

Different output formats handle missing/null values appropriately for their ecosystem:

| Output Type | Integer Nulls | Float Nulls | Boolean Nulls | String Nulls |
|-------------|---------------|-------------|---------------|--------------|
| `list` | `np.nan` | `np.nan` | `np.nan` | `None` |
| `pandas` | `pd.NA` | `np.nan` | `pd.NA` | `pd.NA` |
| `polars` | `None` | `None` | `None` | `None` |

## Type Validation and Error Handling

The library includes comprehensive validation:

- **RSSD ID validation**: Ensures numeric strings (e.g., `"480228"`)
- **Date format validation**: Supports multiple date formats
- **Output type validation**: Validates `output_type` parameter
- **Polars availability**: Graceful error if polars not installed

```python
# Example validation error
try:
    df = collect_data(..., output_type="polars")
except ValueError as e:
    print(e)  # "Polars not available" (if polars not installed)
```

## Performance Considerations

### Memory Efficiency
- **List output**: Most memory efficient (raw Python objects)
- **Pandas output**: Moderate memory usage (nullable types require overhead)
- **Polars output**: Optimized memory usage with columnar storage

### Processing Speed
- **List output**: Fastest (no DataFrame construction)
- **Polars output**: Fast direct conversion
- **Pandas output**: Slower due to type conversion overhead

### Precision Preservation
- **Polars output**: Highest precision (direct conversion)
- **List output**: High precision (numpy types)  
- **Pandas output**: Good precision (nullable types prevent int→float coercion)

## Best Practices

### Choose the Right Output Type

1. **Use `"list"`** when:
   - Building custom data processing pipelines
   - Need maximum performance with minimal memory
   - Working with raw data transformations

2. **Use `"pandas"`** when:
   - Integrating with pandas-based workflows
   - Need mature DataFrame ecosystem
   - Working with mixed data analysis tools

3. **Use `"polars"`** when:
   - Need maximum precision preservation
   - Working with large datasets efficiently
   - Want modern DataFrame performance

### Type Checking

```python
# Check data types in your output
if output_type == "pandas":
    print(df.dtypes)
elif output_type == "polars":
    print(df.schema)
```

### Data Validation

```python
# Validate integer precision preservation
assert df['int_data'].dtype.name == 'Int64'  # pandas
assert df.schema['int_data'] == pl.Int64      # polars
```

## Migration Notes

When upgrading between versions, the type handling ensures:

- **Backward compatibility**: Existing code continues to work
- **Precision preservation**: No data loss in type conversions
- **Consistent schemas**: Same column types across versions

## Examples

### Working with Different Output Types

```python
from ffiec_data_connect import collect_data

# Get data in different formats
list_data = collect_data(..., output_type="list")
pandas_df = collect_data(..., output_type="pandas")
polars_df = collect_data(..., output_type="polars")

# Check integer precision
list_value = list_data[0]['int_data']        # numpy.int64
pandas_value = pandas_df['int_data'].iloc[0]  # numpy.int64 
polars_value = polars_df['int_data'][0]       # int

# All preserve the same precision
assert int(list_value) == pandas_value == polars_value
```

### Type-Specific Operations

```python
# Pandas: Use nullable integer operations
total = pandas_df['int_data'].sum()  # Handles pd.NA correctly

# Polars: Use native polars operations  
total = polars_df.select(pl.col('int_data').sum())

# List: Custom aggregation
total = sum(row['int_data'] for row in list_data 
           if not np.isnan(row['int_data']))
```

This comprehensive type handling ensures that FFIEC financial data maintains its precision and integrity regardless of your preferred data processing framework.