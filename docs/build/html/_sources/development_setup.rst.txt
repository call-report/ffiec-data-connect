=======================
Development Setup
=======================

This guide explains how to set up and run the FFIEC Data Connect library in development mode without installing it via pip. This is useful for contributing to the library, testing changes, or debugging issues.

Prerequisites
=============

System Requirements
-------------------

- Python 3.10 or higher (required for modern type hints and zoneinfo support)
- Git for version control
- Virtual environment tool (venv, virtualenv, or conda)

Clone the Repository
====================

First, clone the repository from GitHub:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/call-report/ffiec-data-connect.git
   cd ffiec-data-connect

   # Or if you have a fork:
   git clone https://github.com/YOUR_USERNAME/ffiec-data-connect.git
   cd ffiec-data-connect

Set Up Virtual Environment
==========================

It's strongly recommended to use a virtual environment for development:

Using venv (Built-in)
---------------------

.. code-block:: bash

   # Create virtual environment
   python -m venv venv

   # Activate it
   # On macOS/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate

Using conda
-----------

.. code-block:: bash

   # Create conda environment
   conda create -n ffiec-dev python=3.10

   # Activate it
   conda activate ffiec-dev

Install Dependencies
====================

Development Mode Installation
-----------------------------

Install the package in "editable" or "development" mode. This allows you to make changes to the code and have them immediately reflected without reinstalling:

.. code-block:: bash

   # Install in editable mode with development dependencies
   pip install -e ".[dev]"

   # If the above doesn't work, try:
   pip install -e .
   pip install -r requirements-dev.txt

Core Dependencies Only
----------------------

If you only need the core dependencies without development tools:

.. code-block:: bash

   # Install core dependencies
   pip install -r requirements.txt

   # Or manually install required packages:
   pip install pandas numpy requests zeep defusedxml

   # Optional: Install polars for polars output support
   pip install polars

Verify Installation
===================

Test that the development installation is working:

.. code-block:: bash

   # Start Python interpreter
   python

.. code-block:: python

   >>> import ffiec_data_connect
   >>> print(ffiec_data_connect.__version__)
   >>> from ffiec_data_connect import credentials, methods
   >>> print("Development setup successful!")

Running Code in Development Mode
=================================

Using the Library from Source
------------------------------

When the library is installed in editable mode, you can use it as if it were installed normally:

.. code-block:: python

   # Your script.py
   from ffiec_data_connect import methods, credentials, ffiec_connection

   # Use the library normally
   creds = credentials.WebserviceCredentials(username="...", password="...")
   # ... rest of your code

Direct Path Import (Alternative)
---------------------------------

If you prefer not to install in editable mode, you can add the source directory to your Python path:

.. code-block:: python

   # Add at the top of your script
   import sys
   import os

   # Add the src directory to Python path
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'path/to/ffiec-data-connect/src'))

   # Now import normally
   import ffiec_data_connect

Using Jupyter Notebooks
-----------------------

For Jupyter notebook development:

.. code-block:: python

   # In the first cell
   import sys
   sys.path.append('/path/to/ffiec-data-connect/src')

   # Now you can import and use the library
   from ffiec_data_connect import methods, credentials

Running Tests
=============

The library includes comprehensive tests. To run them:

Basic Test Run
--------------

.. code-block:: bash

   # Run all tests
   python -m pytest tests/

   # Run specific test file
   python -m pytest tests/unit/test_methods.py

   # Run with verbose output
   python -m pytest tests/ -v

Test Coverage
-------------

.. code-block:: bash

   # Run tests with coverage report
   python -m pytest tests/ --cov=src/ffiec_data_connect --cov-report=html

   # View coverage report
   open htmlcov/index.html  # macOS
   # or
   start htmlcov/index.html  # Windows

Specific Test Patterns
----------------------

.. code-block:: bash

   # Run only unit tests
   python -m pytest tests/unit/

   # Run only integration tests
   python -m pytest tests/integration/

   # Run tests matching a pattern
   python -m pytest tests/ -k "test_collect_data"

Code Quality Tools
==================

Linting and Formatting
----------------------

The project uses ruff for linting and formatting:

.. code-block:: bash

   # Run linting
   ruff check src/

   # Auto-fix linting issues
   ruff check src/ --fix

   # Format code
   ruff format src/

Type Checking
-------------

If mypy is configured:

.. code-block:: bash

   # Run type checking
   mypy src/ffiec_data_connect

Building Documentation
======================

To build and test documentation locally:

.. code-block:: bash

   # Install documentation dependencies
   pip install sphinx sphinx-rtd-theme

   # Build HTML documentation
   cd docs
   make clean
   make html

   # View documentation
   open build/html/index.html  # macOS
   # or
   start build/html/index.html  # Windows

Making Changes
==============

Development Workflow
--------------------

1. **Create a feature branch**:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

2. **Make your changes** in the source code

3. **Test your changes**:

   .. code-block:: bash

      # Run relevant tests
      python -m pytest tests/unit/test_methods.py

      # Check linting
      ruff check src/

4. **Test manually** with a script:

   .. code-block:: python

      # test_script.py
      from ffiec_data_connect import methods, credentials

      # Test your changes
      # ...

5. **Commit your changes**:

   .. code-block:: bash

      git add .
      git commit -m "feat: description of your changes"

Common Development Tasks
========================

Adding a New Feature
--------------------

1. Write the feature code in the appropriate module
2. Add tests in ``tests/unit/`` or ``tests/integration/``
3. Update documentation if needed
4. Run full test suite to ensure nothing broke

Debugging
---------

For debugging, you can add breakpoints in the source code:

.. code-block:: python

   # In any source file
   import pdb; pdb.set_trace()  # Add breakpoint

   # Or use the built-in breakpoint (Python 3.7+)
   breakpoint()

Then run your script normally, and execution will pause at the breakpoint.

Logging
-------

Enable debug logging to see detailed execution:

.. code-block:: python

   import logging

   # Enable debug logging for the library
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger('ffiec_data_connect')
   logger.setLevel(logging.DEBUG)

Project Structure
=================

Understanding the project structure helps with development:

.. code-block:: text

   ffiec-data-connect/
   ├── src/
   │   └── ffiec_data_connect/
   │       ├── __init__.py           # Package initialization
   │       ├── credentials.py        # Credential handling
   │       ├── methods.py            # Main API methods
   │       ├── methods_enhanced.py   # REST API enhancements
   │       ├── ffiec_connection.py   # SOAP connection handling
   │       ├── protocol_adapter.py   # REST/SOAP adapter
   │       ├── xbrl_processor.py     # XBRL data processing
   │       └── ...
   ├── tests/
   │   ├── unit/                     # Unit tests
   │   └── integration/              # Integration tests
   ├── docs/
   │   ├── source/                   # Documentation source (RST)
   │   └── build/                    # Built documentation
   ├── requirements.txt              # Core dependencies
   ├── requirements-dev.txt          # Development dependencies
   └── setup.py                      # Package configuration

Environment Variables
=====================

For development, you may need to set environment variables:

.. code-block:: bash

   # For testing with credentials (create .env file)
   export FFIEC_USERNAME="your_username"
   export FFIEC_PASSWORD="your_password"
   export FFIEC_TOKEN="your_token"  # For REST API

   # Or use a .env file with python-dotenv
   pip install python-dotenv

Then in your code:

.. code-block:: python

   from dotenv import load_dotenv
   import os

   load_dotenv()

   username = os.getenv('FFIEC_USERNAME')
   password = os.getenv('FFIEC_PASSWORD')

Troubleshooting Development Setup
==================================

Import Errors
-------------

If you get ``ModuleNotFoundError``:

1. Ensure you're in the activated virtual environment
2. Verify the package is installed in editable mode: ``pip list | grep ffiec``
3. Check that the src directory is in your Python path

Dependency Conflicts
--------------------

If you encounter dependency conflicts:

.. code-block:: bash

   # Create a fresh virtual environment
   deactivate
   rm -rf venv/
   python -m venv venv
   source venv/bin/activate
   pip install -e .

Permission Errors
-----------------

On macOS/Linux, you might need to make scripts executable:

.. code-block:: bash

   chmod +x scripts/*.py

Contributing
============

If you plan to contribute your changes back:

1. Fork the repository on GitHub
2. Create a feature branch from ``main`` or ``develop``
3. Make your changes following the project's coding standards
4. Write tests for new functionality
5. Update documentation as needed
6. Submit a pull request with a clear description

See Also
========

- :doc:`index` - Main documentation
- :doc:`data_type_handling` - Understanding type handling
- :doc:`examples` - Usage examples
- `GitHub Repository <https://github.com/call-report/ffiec-data-connect>`_
