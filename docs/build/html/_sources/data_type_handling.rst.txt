=======================
Data Type Handling
=======================

FFIEC Data Connect provides comprehensive data type handling across multiple protocols (SOAP/REST) and output formats, ensuring data integrity and precision from the original XBRL source through to your final data structure.

Overview
========

The library manages data types across three key dimensions:

Protocol Layer (SOAP vs REST)
------------------------------

.. list-table:: Protocol Comparison
   :widths: 20 40 40
   :header-rows: 1

   * - Aspect
     - SOAP API
     - REST API
   * - Credentials
     - ``WebserviceCredentials``
     - ``OAuth2Credentials``
   * - Null Values
     - ``np.nan`` (NumPy)
     - ``pd.NA`` (Pandas)
   * - Compatibility
     - 100% backward compatible
     - Enhanced integer handling
   * - Use Case
     - Existing integrations
     - New implementations

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
     - Monetary values (÷1000)
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
3. **Null Handling**: Protocol-specific null values applied

SOAP vs REST Null Handling
===========================

Why Different Null Handling Strategies?
----------------------------------------

The library uses different null strategies for SOAP and REST to solve a critical problem while maintaining backward compatibility:

**The Problem:**

When pandas DataFrames contained ``np.nan`` values in integer columns, pandas would automatically convert those columns to ``float64`` to accommodate the NaN values. This resulted in integer values displaying with decimal points (e.g., ``1000.0`` instead of ``1000``), which was both aesthetically problematic and semantically incorrect for financial data that should be represented as whole numbers.

**The Solution:**

1. **SOAP Path (Original)**: Continues using ``np.nan`` to ensure 100% backward compatibility for existing integrations. Existing code that expects ``np.nan`` behavior continues to work unchanged.

2. **REST Path (Enhanced)**: Uses ``pd.NA``, which is pandas' newer null value that works with nullable integer types (``Int64``). This allows integer columns to remain as integers even when containing null values.

**Design Philosophy:**

This dual approach follows the principle of "never break existing code." Users who have built systems around the SOAP API can upgrade the library without any changes to their code, while new REST API users automatically benefit from improved type handling.

.. code-block:: python

   # Example of the problem this solves:
   # Before (with np.nan):
   df['int_data']  # Shows: [1000.0, 2000.0, NaN, 3000.0]

   # After (with pd.NA for REST):
   df['int_data']  # Shows: [1000, 2000, <NA>, 3000]

Technical Implementation
------------------------

The differentiation between SOAP and REST null handling is implemented at the XBRL processor level through the ``use_rest_nulls`` parameter:

- **SOAP calls**: Automatically use ``use_rest_nulls=False`` (default), applying ``np.nan``
- **REST calls**: Explicitly set ``use_rest_nulls=True``, applying ``pd.NA``
- **User transparency**: This is handled automatically based on credential type - users never need to specify this parameter

This approach ensures that:

1. **Zero configuration needed**: The library automatically selects the appropriate null handling based on your credentials
2. **No breaking changes**: Existing SOAP users see no changes in behavior
3. **Optimal for each protocol**: Each API path gets the most appropriate null handling for its use case
4. **Future-proof**: As pandas evolves, REST users automatically benefit from improvements to nullable types

SOAP API (Original Behavior)
-----------------------------

.. list-table:: SOAP Null Value Handling
   :widths: 20 20 30 30
   :header-rows: 1

   * - Data Type
     - Null Value
     - Pandas Conversion
     - Final dtype
   * - Integer
     - ``np.nan``
     - Direct to ``Int64``
     - Nullable integer
   * - Float
     - ``np.nan``
     - Direct to ``float64``
     - Standard float
   * - Boolean
     - ``np.nan``
     - Direct to ``boolean``
     - Nullable boolean
   * - String
     - ``None``
     - Direct to ``string``
     - Pandas string

.. code-block:: python

   # SOAP path - original behavior preserved
   processed_ret = xbrl_processor._process_xml(
       data,
       date_format,
       use_rest_nulls=False  # Default
   )

REST API (Enhanced Behavior)
-----------------------------

.. list-table:: REST Null Value Handling
   :widths: 15 15 20 25 25
   :header-rows: 1

   * - Data Type
     - Null Value
     - Intermediate
     - Pandas Conversion
     - Final dtype
   * - Integer
     - ``pd.NA``
     - → ``None``
     - → ``Int64``
     - Nullable integer
   * - Float
     - ``pd.NA``
     - → ``np.nan``
     - → ``float64``
     - Standard float
   * - Boolean
     - ``pd.NA``
     - → ``None``
     - → ``boolean``
     - Nullable boolean
   * - String
     - ``None``
     - (unchanged)
     - → ``string``
     - Pandas string

.. code-block:: python

   # REST path - enhanced handling
   processed_ret = xbrl_processor._process_xml(
       data,
       date_format,
       use_rest_nulls=True  # Explicit for REST
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

Current Behavior - SOAP Path
-----------------------------

.. code-block:: python

   # Input: XBRL with USD value "1500000"
   # Processing: 1500000 // 1000 = 1500 (integer division)
   # Storage: np.int64(1500) with np.nan for nulls
   # DataFrame: Int64 dtype
   # Display: 1500 (no .0 suffix)

Current Behavior - REST Path
-----------------------------

.. code-block:: python

   # Input: JSON with integer 1500000
   # Processing: 1500000 // 1000 = 1500
   # Storage: np.int64(1500) with pd.NA for nulls
   # Conversion: pd.NA → None → Int64
   # Display: 1500 (no .0 suffix)

Type Conversion Decision Tree
==============================

.. code-block:: text

   Input Data
       ├── SOAP API (WebserviceCredentials)
       │   ├── XBRL Processing
       │   │   ├── Detect Type (USD/PURE/etc.)
       │   │   └── Apply np.nan for nulls
       │   └── Output Format
       │       ├── list → Raw dicts with np.nan
       │       ├── pandas → DataFrame with Int64/float64/boolean
       │       └── polars → DataFrame with native nullable types
       │
       └── REST API (OAuth2Credentials)
           ├── XBRL Processing
           │   ├── Detect Type
           │   └── Apply pd.NA for nulls
           └── Output Format
               ├── list → Raw dicts with pd.NA
               ├── pandas → Convert pd.NA → None/np.nan → nullable dtypes
               └── polars → Convert pd.NA → None → native nulls

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

Migration Guide
===============

From Existing SOAP Integration
-------------------------------

No changes required. The library maintains 100% backward compatibility:

.. code-block:: python

   # Existing code continues to work unchanged
   df = collect_data(
       session=connection.session,
       creds=soap_credentials,
       reporting_period="2023-12-31",
       rssd_id="480228",
       output_type="pandas"
   )
   # Returns DataFrame with same types as before

Adopting REST API
-----------------

To leverage enhanced REST features:

.. code-block:: python

   # Use OAuth2Credentials for REST
   creds = OAuth2Credentials(username="user", token="token")

   df = collect_data(
       session=None,  # Not needed for REST
       creds=creds,
       reporting_period="2023-12-31",
       rssd_id="480228",
       output_type="pandas"
   )
   # Returns DataFrame with enhanced null handling

Overriding Null Value Handling
===============================

The ``force_null_types`` Parameter
-----------------------------------

While the library automatically selects the appropriate null handling based on your API choice (SOAP vs REST), you can override this behavior using the ``force_null_types`` parameter available in ``collect_data()`` and ``collect_ubpr_facsimile_data()`` functions.

**When to Use This Parameter:**

1. **Testing and Migration**: Test how your code would behave with different null handling before switching APIs
2. **Compatibility Issues**: Work around specific compatibility requirements in your data pipeline
3. **Performance Comparison**: Compare the behavior of both null handling approaches
4. **Gradual Migration**: SOAP users can preview REST-style null handling without changing credentials

Parameter Options
-----------------

.. list-table:: force_null_types Options
   :widths: 20 40 40
   :header-rows: 1

   * - Value
     - Behavior
     - Use Case
   * - ``None`` (default)
     - Automatic based on API type
     - Normal operation - recommended
   * - ``"numpy"``
     - Force ``np.nan`` for all null values
     - Legacy compatibility, SOAP-like behavior
   * - ``"pandas"``
     - Force ``pd.NA`` for null values
     - Better integer display, REST-like behavior

Usage Examples
--------------

**Example 1: SOAP User Testing Pandas Null Handling**

.. code-block:: python

   # SOAP credentials normally use np.nan
   soap_creds = WebserviceCredentials(username="user", password="pass")

   # Test with pandas null handling without switching to REST
   df = collect_data(
       session=connection.session,
       creds=soap_creds,
       reporting_period="2023-12-31",
       rssd_id="480228",
       output_type="pandas",
       force_null_types="pandas"  # Override to use pd.NA
   )
   # Now integers display without .0 suffix

**Example 2: REST User Requiring NumPy Compatibility**

.. code-block:: python

   # REST credentials normally use pd.NA
   rest_creds = OAuth2Credentials(username="user", token="token")

   # Force numpy nulls for compatibility with legacy analysis code
   df = collect_data(
       session=None,
       creds=rest_creds,
       reporting_period="2023-12-31",
       rssd_id="480228",
       output_type="pandas",
       force_null_types="numpy"  # Override to use np.nan
   )
   # Now compatible with code expecting np.nan

**Example 3: Comparing Both Approaches**

.. code-block:: python

   # Compare integer handling with different null types
   for null_type in [None, "numpy", "pandas"]:
       df = collect_data(
           session=connection.session,
           creds=credentials,
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

1. **Use defaults when possible**: Let the library choose based on your API
2. **Document overrides**: If you override, comment why in your code
3. **Test thoroughly**: When overriding, test all data operations
4. **Consider migration**: If consistently overriding, consider switching APIs

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

Performance Considerations
==========================

.. list-table:: Performance Comparison
   :widths: 25 25 25 25
   :header-rows: 1

   * - Operation
     - SOAP
     - REST
     - Notes
   * - Null checking
     - Fast (``np.isnan``)
     - Fast (``pd.isna``)
     - Both optimized
   * - DataFrame creation
     - Standard
     - Slightly slower
     - REST has extra conversion
   * - Memory usage
     - Standard
     - ~Same
     - Nullable types similar
   * - Integer operations
     - Fast
     - Fast
     - Int64 optimized

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
   :widths: 25 20 25 30
   :header-rows: 1

   * - Function
     - Purpose
     - SOAP Behavior
     - REST Behavior
   * - ``_process_xml()``
     - Parse XBRL
     - Uses ``np.nan``
     - Uses ``pd.NA`` with ``use_rest_nulls=True``
   * - ``_process_xbrl_item()``
     - Process single item
     - Returns typed value
     - Returns typed value
   * - DataFrame conversion
     - Create pandas DF
     - Direct with ``np.nan``
     - Converts ``pd.NA`` → appropriate nulls

Version History
===============

- **v2.0.0**: Added REST API support with enhanced null handling
- **v1.x.x**: Original SOAP-only implementation with ``np.nan``

See Also
========

- `Pandas Nullable Integer Documentation <https://pandas.pydata.org/docs/user_guide/integer_na.html>`_
- `Polars Data Types <https://pola-rs.github.io/polars/py-polars/html/reference/datatypes.html>`_
- `NumPy Data Types <https://numpy.org/doc/stable/user/basics.types.html>`_
