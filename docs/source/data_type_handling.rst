=======================
Data Type Handling
=======================

FFIEC Data Connect provides comprehensive data type handling across multiple output formats, ensuring data integrity and precision from the original XBRL source through to your final data structure.

Overview
========

The library manages data types across two key dimensions:

1. **Type Detection**: Automatic detection from XBRL unit references
2. **Output Formatting**: Proper type mapping for list, pandas, and polars outputs

Type Detection in XBRL Processing
==================================

The library automatically detects data types from XBRL unit references:

.. list-table:: XBRL Type Mapping
   :widths: 20 20 20 40
   :header-rows: 1

   * - XBRL Unit
     - Value Example
     - Python Type
     - Description
   * - ``USD``
     - ``"1500000"``
     - ``np.int64``
     - Monetary values (divided by 1000)
   * - ``PURE``
     - ``"1.25"``
     - ``np.float64``
     - Ratios and percentages
   * - ``NON-MONETARY``
     - ``"0.85"``
     - ``np.float64``
     - Non-monetary numerics
   * - Boolean
     - ``"true"/"false"``
     - ``np.bool_``
     - Boolean indicators
   * - Other
     - ``"text"``
     - ``str``
     - Text values

Special Processing Rules
------------------------

1. **USD Values**: Automatically divided by 1000 using integer division (``//``)
2. **Type Preservation**: Original types stored in ``data_type`` field
3. **Null Handling**: Uses ``pd.NA`` for proper nullable type support

Null Value Handling
====================

The library uses ``pd.NA`` (pandas' native nullable marker), which works with nullable integer types (``Int64``). This allows integer columns to remain as integers even when containing null values.

.. code-block:: python

   # With pd.NA:
   df['int_data']  # Shows: [1000, 2000, <NA>, 3000]

Technical Implementation
------------------------

Null handling is implemented at the XBRL processor level through the ``use_rest_nulls`` parameter:

- REST calls use ``use_rest_nulls=True``, applying ``pd.NA``
- This is handled automatically -- users never need to specify this parameter

This approach ensures that:

1. **Zero configuration needed**: The library automatically selects the appropriate null handling
2. **Optimal display**: Integer columns display without ``.0`` suffixes
3. **Future-proof**: As pandas evolves, users automatically benefit from improvements to nullable types

.. list-table:: Null Value Handling
   :widths: 15 15 20 25 25
   :header-rows: 1

   * - Data Type
     - Null Value
     - Intermediate
     - Pandas Conversion
     - Final dtype
   * - Integer
     - ``pd.NA``
     - -> ``None``
     - -> ``Int64``
     - Nullable integer
   * - Float
     - ``pd.NA``
     - -> ``np.nan``
     - -> ``float64``
     - Standard float
   * - Boolean
     - ``pd.NA``
     - -> ``None``
     - -> ``boolean``
     - Nullable boolean
   * - String
     - ``None``
     - (unchanged)
     - -> ``string``
     - Pandas string

.. code-block:: python

   # REST path - enhanced handling
   processed_ret = xbrl_processor._process_xml(
       data,
       date_format,
       use_rest_nulls=True
   )

Output Format Type Mapping
==========================

List Output (``output_type="list"``)
-------------------------------------

Returns raw dictionaries with the following structure:

.. code-block:: python

   {
       'mdrm': str,              # MDRM identifier
       'rssd': str,              # RSSD ID
       'quarter': str/date,      # Based on date_output_format
       'data_type': str,         # 'int', 'float', 'bool', or 'str'
       'int_data': int/null,     # Value if data_type='int'
       'float_data': float/null, # Value if data_type='float'
       'bool_data': bool/null,   # Value if data_type='bool'
       'str_data': str/None      # Value if data_type='str'
   }

Pandas Output (``output_type="pandas"``)
-----------------------------------------

Creates DataFrames with nullable types for proper null handling:

.. list-table:: Pandas Column Types
   :widths: 20 20 40 20
   :header-rows: 1

   * - Column
     - dtype
     - Description
     - Null Support
   * - ``mdrm``
     - ``object``
     - MDRM identifier
     - No
   * - ``rssd``
     - ``object``
     - RSSD ID as string
     - No
   * - ``quarter``
     - ``object``/``datetime64``
     - Based on date_output_format
     - No
   * - ``data_type``
     - ``object``
     - Type indicator
     - No
   * - ``int_data``
     - ``Int64``
     - Nullable integer
     - Yes (``pd.NA``)
   * - ``float_data``
     - ``float64``
     - Standard float
     - Yes (``NaN``)
   * - ``bool_data``
     - ``boolean``
     - Nullable boolean
     - Yes (``pd.NA``)
   * - ``str_data``
     - ``string``
     - Pandas string
     - Yes (``pd.NA``)

**Key Benefits:**

- No ``.0`` suffix on integer values
- Proper null handling with pandas nullable types
- Type-safe operations

Polars Output (``output_type="polars"``)
-----------------------------------------

Direct conversion with native nullable types:

.. list-table:: Polars Schema
   :widths: 20 25 20 35
   :header-rows: 1

   * - Column
     - Polars Type
     - Null Support
     - Notes
   * - ``mdrm``
     - ``pl.Utf8``
     - No
     - String type
   * - ``rssd``
     - ``pl.Utf8``
     - No
     - String type
   * - ``quarter``
     - ``pl.Utf8``/``pl.Date``
     - No
     - Based on date_output_format
   * - ``data_type``
     - ``pl.Utf8``
     - No
     - String type
   * - ``int_data``
     - ``pl.Int64``
     - Yes
     - Native nullable
   * - ``float_data``
     - ``pl.Float64``
     - Yes
     - Native nullable
   * - ``bool_data``
     - ``pl.Boolean``
     - Yes
     - Native nullable
   * - ``str_data``
     - ``pl.Utf8``
     - Yes
     - Native nullable

Integer Display Examples
========================

Problem Scenario (Before Fix)
------------------------------

.. code-block:: python

   # Original issue: integers showing as floats
   df['int_data']  # Shows: 1000.0, 2000.0, 3000.0

Current Behavior
-----------------

.. code-block:: python

   # Input: JSON with integer 1500000
   # Processing: 1500000 // 1000 = 1500
   # Storage: np.int64(1500) with pd.NA for nulls
   # Conversion: pd.NA -> None -> Int64
   # Display: 1500 (no .0 suffix)

Type Conversion Decision Tree
==============================

.. code-block:: text

   Input Data
       └── REST API (OAuth2Credentials)
           ├── XBRL Processing
           │   ├── Detect Type (USD/PURE/etc.)
           │   └── Apply pd.NA for nulls
           └── Output Format
               ├── list -> Raw dicts with pd.NA
               ├── pandas -> Convert pd.NA -> None/np.nan -> nullable dtypes
               └── polars -> Convert pd.NA -> None -> native nulls

Date Format Handling
====================

The ``date_output_format`` parameter affects the ``quarter`` column:

.. list-table:: Date Format Options
   :widths: 25 25 20 15 15
   :header-rows: 1

   * - Format
     - Example Output
     - Python Type
     - Pandas dtype
     - Polars Type
   * - ``"string_original"``
     - ``"12/31/2023"``
     - ``str``
     - ``object``
     - ``pl.Utf8``
   * - ``"string_yyyymmdd"``
     - ``"20231231"``
     - ``str``
     - ``object``
     - ``pl.Utf8``
   * - ``"python_format"``
     - ``datetime(2023,12,31)``
     - ``datetime``
     - ``datetime64[ns]``
     - ``pl.Date``

Common Patterns and Best Practices
===================================

Working with Integer Data
--------------------------

.. code-block:: python

   # Recommended: Use nullable integer operations
   df['int_data'].sum()      # Handles NA/null correctly
   df['int_data'].fillna(0)  # Replace nulls with 0

   # Avoid: Converting to standard float
   float(df['int_data'])  # May raise error with NA values

Type Checking
-------------

.. code-block:: python

   # Check for integer rows
   int_rows = df[df['data_type'] == 'int']

   # Access specific typed columns
   integers = df['int_data'].dropna()
   floats = df['float_data'].dropna()

Null Handling
-------------

.. code-block:: python

   # Pandas: Use pd.isna() for universal null checking
   pd.isna(df['int_data'])  # Works with both NaN and NA

   # Polars: Use native is_null()
   df_polars['int_data'].is_null()

Type Preservation During Operations
------------------------------------

.. code-block:: python

   # Maintains Int64 type
   df['int_data'] * 1000   # Result is still Int64

   # Converts to float64
   df['int_data'] / 1000   # Result becomes float64
   df['int_data'] // 1000  # Use // to maintain integer

Overriding Null Value Handling
===============================

The ``force_null_types`` Parameter
-----------------------------------

While the library automatically uses ``pd.NA`` for null handling, you can override this behavior using the ``force_null_types`` parameter available in ``collect_data()`` and ``collect_ubpr_facsimile_data()`` functions.

**When to Use This Parameter:**

1. **Compatibility Issues**: Work around specific compatibility requirements in your data pipeline
2. **Legacy Code**: Force ``np.nan`` behavior for code that expects it

Parameter Options
-----------------

.. list-table:: force_null_types Options
   :widths: 20 40 40
   :header-rows: 1

   * - Value
     - Behavior
     - Use Case
   * - ``None`` (default)
     - Uses ``pd.NA`` for null values
     - Normal operation - recommended
   * - ``"numpy"``
     - Force ``np.nan`` for all null values
     - Legacy compatibility
   * - ``"pandas"``
     - Force ``pd.NA`` for null values
     - Explicit selection (same as default)

Usage Examples
--------------

**Example 1: Forcing NumPy Compatibility**

.. code-block:: python

   # Force numpy nulls for compatibility with legacy analysis code
   df = collect_data(
       creds,
       reporting_period="2023-12-31",
       rssd_id="480228",
       output_type="pandas",
       force_null_types="numpy"  # Override to use np.nan
   )
   # Now compatible with code expecting np.nan

**Example 2: Comparing Both Approaches**

.. code-block:: python

   # Compare integer handling with different null types
   for null_type in [None, "numpy", "pandas"]:
       df = collect_data(
           creds,
           reporting_period="2023-12-31",
           rssd_id="480228",
           output_type="pandas",
           force_null_types=null_type
       )
       print(f"Null type: {null_type or 'automatic'}")
       print(f"Integer sample: {df['int_data'].iloc[0]}")
       print(f"Has .0 suffix: {'.0' in str(df['int_data'].iloc[0])}\n")

Implementation Notes
--------------------

- **Performance**: No significant performance difference between null types
- **Memory Usage**: ``pd.NA`` uses slightly more memory but provides better type safety
- **Compatibility**: ``np.nan`` is more widely compatible with older pandas versions
- **Future-Proof**: ``pd.NA`` is the recommended approach for new pandas code

Best Practices
--------------

1. **Use defaults when possible**: Let the library choose automatically
2. **Document overrides**: If you override, comment why in your code
3. **Test thoroughly**: When overriding, test all data operations

.. warning::

   Overriding null types may cause unexpected behavior if your code assumes specific null handling. Test thoroughly when using ``force_null_types``.

Troubleshooting
===============

NAType Error
------------

**Symptom:** ``float() argument must be a string or a real number, not 'NAType'``

**Cause:** Attempting float conversion on pandas NA value

**Solution:** Use ``pd.isna()`` for null checking or ``.fillna()`` before conversion

Integers Display with .0
------------------------

**Symptom:** Integer values show as ``1000.0`` instead of ``1000``

**Cause:** Mixed with float or using regular division

**Solution:** Ensure using Int64 dtype and integer division (``//``)

Type Loss in Operations
-----------------------

**Symptom:** Int64 column becomes float64 after operation

**Cause:** Operation that produces non-integer results

**Solution:** Use integer-preserving operations or explicitly cast back

API Reference
=============

Type-Related Parameters
-----------------------

.. list-table:: Parameters
   :widths: 20 30 20 30
   :header-rows: 1

   * - Parameter
     - Options
     - Default
     - Description
   * - ``output_type``
     - ``"list"``, ``"pandas"``, ``"polars"``
     - ``"list"``
     - Output format
   * - ``date_output_format``
     - ``"string_original"``, ``"string_yyyymmdd"``, ``"python_format"``
     - ``"string_original"``
     - Date format in output

Internal Type Handling
----------------------

.. list-table:: Internal Functions
   :widths: 25 25 50
   :header-rows: 1

   * - Function
     - Purpose
     - Behavior
   * - ``_process_xml()``
     - Parse XBRL
     - Uses ``pd.NA`` with ``use_rest_nulls=True``
   * - ``_process_xbrl_item()``
     - Process single item
     - Returns typed value
   * - DataFrame conversion
     - Create pandas DF
     - Converts ``pd.NA`` -> appropriate nulls

Version History
===============

- **v3.0.0**: SOAP removed. REST-only with ``pd.NA`` null handling
- **v2.0.0**: Added REST API support with enhanced null handling
- **v1.x.x**: Original SOAP-only implementation with ``np.nan``

See Also
========

- `Pandas Nullable Integer Documentation <https://pandas.pydata.org/docs/user_guide/integer_na.html>`_
- `Polars Data Types <https://pola-rs.github.io/polars/py-polars/html/reference/datatypes.html>`_
- `NumPy Data Types <https://numpy.org/doc/stable/user/basics.types.html>`_
