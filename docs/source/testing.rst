=============
Testing Guide
=============

.. note::

   This guide is for developers contributing to or modifying the
   ``ffiec-data-connect`` library. If you are just using the library,
   you do not need to run these tests.

Overview
========

The ``ffiec-data-connect`` test suite uses `pytest
<https://docs.pytest.org/>`_ and is organized into two layers:

- **Unit tests** (``tests/unit/``) — 606 tests that run fully offline against
  mocks and fixtures. No network access or credentials are required.
- **Integration tests** (``tests/integration/``) — 26 live tests that exercise
  the real FFIEC REST API. They are skipped automatically when credentials
  are not provided.

The unit test suite achieves **100% statement coverage** and ~99.7% branch
coverage of the ``ffiec_data_connect`` package. Continuous integration runs
the suite on Python 3.10, 3.11, 3.12, and 3.13.

See the ``TESTS.md`` file in the repository root for a complete, per-test
catalog with descriptions.

Setup
=====

Clone the repository and install the package in editable mode with the
development extras:

.. code-block:: bash

   git clone https://github.com/call-report/ffiec-data-connect.git
   cd ffiec-data-connect

   # Create a virtual environment (any tool works: venv, uv, virtualenv, conda)
   python -m venv .venv
   source .venv/bin/activate

   # Install with dev extras (pytest, black, mypy, etc.) plus polars for
   # tests that cover the polars output path
   pip install -e ".[dev,polars]"

The ``Makefile`` exposes a convenience target that installs every optional
extra needed for tests, docs, and notebooks:

.. code-block:: bash

   make install-dev     # pip install -e ".[dev,docs,notebook,polars]"

See :doc:`development_setup` for more detail on setting up a development
environment.

Running Unit Tests
==================

Unit tests do not require any credentials or network access. Run the full
unit-test suite with:

.. code-block:: bash

   make test
   # equivalent to: python -m pytest tests/unit/ -v

For a fast iteration loop while working on core modules, run just the
credentials, methods, and calling-convention tests:

.. code-block:: bash

   make test-fast

You can also invoke ``pytest`` directly for finer-grained runs.

Run a single test file:

.. code-block:: bash

   pytest tests/unit/test_credentials.py -v

Run a single test class:

.. code-block:: bash

   pytest tests/unit/test_credentials.py::TestOAuth2Credentials -v

Run a single test method:

.. code-block:: bash

   pytest tests/unit/test_credentials.py::TestOAuth2Credentials::test_valid_token -v

Run all tests matching a keyword expression:

.. code-block:: bash

   pytest tests/unit/ -k "credentials and not legacy" -v

Select or deselect tests by marker:

.. code-block:: bash

   pytest tests/unit/ -m "not slow"       # skip slow tests
   pytest tests/unit/ -m "unit"           # only tests marked @pytest.mark.unit

The registered markers are defined in ``pyproject.toml``:

- ``unit`` — unit-test marker
- ``integration`` — integration-test marker
- ``slow`` — long-running tests (memory leaks, thread safety, etc.)

Running Integration Tests
=========================

Integration tests in ``tests/integration/test_rest_api_live.py`` hit the real
FFIEC REST API and require valid credentials. They are **automatically
skipped** when the environment variables are not set, so they will not cause
failures in a default ``make test-all`` run on a developer machine without
credentials.

Required environment variables
-------------------------------

- ``FFIEC_USERNAME`` — your FFIEC portal username
- ``FFIEC_BEARER_TOKEN`` — a JWT bearer token (90-day lifecycle)

Obtaining a bearer token
------------------------

1. Register for an account at the FFIEC Central Data Repository Public Data
   Distribution (CDR PDD) portal.
2. Log in and navigate to the account/API section to request a REST API
   bearer token.
3. The token is a JWT that begins with ``ey`` and is valid for 90 days. Store
   it securely; do not commit it to version control.

See :doc:`account_setup` for full account-registration instructions.

Running the integration suite
-----------------------------

.. code-block:: bash

   FFIEC_USERNAME='your_username' \
   FFIEC_BEARER_TOKEN='eyJ...' \
   pytest tests/integration/test_rest_api_live.py -v

To run the full suite (unit + integration) with credentials:

.. code-block:: bash

   FFIEC_USERNAME='your_username' \
   FFIEC_BEARER_TOKEN='eyJ...' \
   make test-all

What the integration tests cover
--------------------------------

The live tests exercise every public REST endpoint against real data for a
known reference bank (JPMorgan Chase, RSSD ``480228``) and reporting period
(``12/31/2024``):

- ``collect_reporting_periods`` — Call and UBPR series, list and pandas output
- ``collect_data`` — RetrieveFacsimile with multiple date input formats and
  ``force_null_types`` variants
- ``collect_filers_on_reporting_period`` — PanelOfReporters, including ZIP
  code string preservation and dual RSSD field validation
- ``collect_filers_since_date`` — FilersSinceDate
- ``collect_filers_submission_date_time`` — submission timestamps
- ``collect_ubpr_reporting_periods`` — UBPR reporting periods (REST-only)
- ``collect_ubpr_facsimile_data`` — UBPR facsimile data (REST-only)
- SOAP deprecation behavior when a session is provided
- JWT ``exp`` claim extraction and expiry detection

If your token has expired, every test is skipped at fixture setup with a
clear message rather than producing cryptic auth failures.

Coverage Reports
================

Generate a terminal coverage report with missing lines:

.. code-block:: bash

   make coverage
   # python -m pytest tests/unit/ --cov=src/ffiec_data_connect \
   #     --cov-report=term-missing --cov-config=.coveragerc

Generate an HTML coverage report:

.. code-block:: bash

   make coverage-html

The HTML report is written to ``htmlcov/index.html``. Open it in a browser
to drill into per-file and per-line coverage.

Generate all report formats (HTML, XML, JSON) in a single run — useful when
uploading to coverage services:

.. code-block:: bash

   make coverage-full

Coverage configuration lives in ``.coveragerc`` and the
``[tool.coverage.*]`` sections of ``pyproject.toml``.

Code Quality
============

Before opening a pull request, run the quality checks. These mirror what CI
enforces:

.. code-block:: bash

   make format        # black + isort (auto-formats src/ and tests/)
   make lint          # flake8
   make type-check    # mypy on src/ffiec_data_connect
   make check-all     # format + lint + type-check + test, in sequence

Individual tool invocations:

.. code-block:: bash

   python -m black src/ tests/
   python -m isort src/ tests/
   python -m flake8 src/ tests/
   python -m mypy src/ffiec_data_connect

Style conventions:

- **black** with line length 88 (``[tool.black]`` in ``pyproject.toml``)
- **isort** with the ``black`` profile
- **flake8** with ``max-line-length = 120``; ``E203``, ``W503``, ``E501``
  are ignored, and ``F401`` is ignored in ``__init__.py``
- **mypy** runs in a relaxed configuration with
  ``ignore_missing_imports = true``

Test Organization
=================

::

   tests/
   ├── conftest.py          # Shared fixtures, autouse Config reset
   ├── unit/                # 606 fast, offline unit tests
   │   ├── test_credentials.py
   │   ├── test_methods.py
   │   ├── test_protocol_adapter_v3.py
   │   ├── test_async_compatible.py
   │   ├── test_xbrl_processor.py
   │   └── ...
   ├── integration/         # 26 live REST API tests (skipped without creds)
   │   ├── test_rest_api_live.py
   │   └── test_mock_soap_server.py
   ├── mocks/               # Mock server implementations
   │   └── soap_server.py
   └── fixtures/            # Static test data
       ├── soap_responses/
       ├── wsdl_samples/
       └── xbrl_samples/

- ``tests/unit/`` contains the bulk of the suite. All tests are network-free
  and rely on mocks, fixtures, or small synthetic inputs.
- ``tests/integration/`` contains live-API tests and mock-server-backed
  tests. These may be slower and/or require external resources.
- ``tests/mocks/`` contains in-process mock server implementations used by
  integration tests.
- ``tests/fixtures/`` holds static SOAP response XML, WSDL samples, and
  XBRL sample documents.
- ``tests/conftest.py`` defines shared fixtures and an autouse
  ``reset_config_after_test`` fixture that resets the global ``Config`` state
  between tests so that legacy-error mode and similar toggles do not leak.

Writing New Tests
=================

A few conventions to follow when adding tests:

**Mock credentials with a spec.** Use ``Mock(spec=OAuth2Credentials)`` so
that attribute typos fail fast and the mock matches the real interface:

.. code-block:: python

   from unittest.mock import Mock
   from ffiec_data_connect import OAuth2Credentials

   def test_something():
       creds = Mock(spec=OAuth2Credentials)
       creds.username = "test_user"
       creds.bearer_token = "eyJtest.token."
       # ...

**Do not mutate ``os.environ`` to change Config.** The global ``Config`` is
reset automatically after each test by the ``reset_config_after_test``
autouse fixture in ``tests/conftest.py``. Prefer ``Config.set_legacy_errors``
(or the ``legacy_mode_enabled`` / ``legacy_mode_disabled`` fixtures) over
poking environment variables from within a test:

.. code-block:: python

   from ffiec_data_connect import config

   def test_typed_exceptions_are_raised():
       config.Config.set_legacy_errors(False)
       # ... assert that a typed FFIECError subclass is raised

**Mark tests appropriately.** Apply markers from ``pyproject.toml`` so they
can be selected or excluded:

.. code-block:: python

   import pytest

   @pytest.mark.integration
   def test_live_endpoint(live_creds):
       ...

   @pytest.mark.slow
   def test_large_batch():
       ...

**Integration tests should auto-skip without credentials.** Follow the
pattern in ``tests/integration/test_rest_api_live.py``: read the env vars in
a module-scoped fixture and call ``pytest.skip(...)`` if they are missing,
rather than failing.

**Keep unit tests offline.** Any test that reaches out over the network
belongs under ``tests/integration/``, not ``tests/unit/``. The unit suite
must remain runnable without credentials or connectivity.

Continuous Integration
======================

GitHub Actions runs the test suite on every push and pull request. The
matrix covers Python 3.10, 3.11, 3.12, and 3.13 on Linux.

- **Pull request workflow** — runs unit tests, coverage, lint, and
  type-checking across the full Python matrix. Integration tests are not
  run in PR CI because they require secret credentials.
- **Main branch workflow** — additionally runs extended tests (memory
  leaks, thread safety) on the main branch only.

When a check fails in CI, reproduce it locally with ``make check-all``
before pushing a fix.

See Also
========

- :doc:`development_setup` — Development environment setup
- :doc:`account_setup` — Obtaining FFIEC credentials and a REST bearer token
- ``TESTS.md`` in the repository root — Full test catalog with per-test
  descriptions
