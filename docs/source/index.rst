ffiec-data-connect documentation has moved
==========================================

The narrative documentation for ``ffiec-data-connect`` now lives at
`call.report <https://call.report/library/ffiec-data-connect>`_.

This page remains at its original URL so older bookmarks and search results
keep working, but everything below has been rewritten, reorganized, and is
actively maintained there.

Start here
----------

- `Install <https://call.report/library/ffiec-data-connect/install>`_ — ``pip install --pre ffiec-data-connect``.
- `Authentication <https://call.report/library/ffiec-data-connect/auth>`_ — JWT bearer tokens from the FFIEC CDR portal.
- `Quickstart <https://call.report/library/ffiec-data-connect/quickstart>`_ — first data pull in under two minutes.

Reference
---------

- `Library overview <https://call.report/library/ffiec-data-connect>`_ — catalog of the full reference.
- `collect_* functions <https://call.report/library/ffiec-data-connect/functions>`_ — the seven module-level data-retrieval functions.
- `Credentials <https://call.report/library/ffiec-data-connect/credentials>`_ — ``OAuth2Credentials``.
- `Client and adapters <https://call.report/library/ffiec-data-connect/client>`_ — ``AsyncCompatibleClient``, ``RateLimiter``, ``RESTAdapter``.
- `Exceptions <https://call.report/library/ffiec-data-connect/exceptions>`_ — ``FFIECError`` and its subclasses.
- `REST API reference <https://call.report/library/ffiec-data-connect/rest-api>`_ — the underlying HTTP surface, with an interactive OpenAPI viewer at `/api/ <https://call.report/api/>`_.

Workflows
---------

- `Output formats <https://call.report/library/ffiec-data-connect/output-formats>`_ — list / pandas / polars; null handling.
- `Bulk download <https://call.report/library/ffiec-data-connect/bulk-download>`_ — pulling many institutions.
- `Async and rate limits <https://call.report/library/ffiec-data-connect/async-and-rate-limits>`_ — the 2,500/hr ceiling.
- `Incremental updates <https://call.report/library/ffiec-data-connect/incremental-updates>`_ — detect refilings.
- `Peer analysis <https://call.report/library/ffiec-data-connect/peer-analysis>`_ — UBPR peer comparisons.

Operations
----------

- `Troubleshooting <https://call.report/library/ffiec-data-connect/troubleshooting>`_ — errors by frequency.
- `Migration from v2 <https://call.report/library/ffiec-data-connect/migration-from-v2>`_ — SOAP removal and the new calling convention.

Contributing
------------

- `Development setup <https://call.report/library/ffiec-data-connect/development>`_ — running from source.
- `Testing <https://call.report/library/ffiec-data-connect/testing>`_ — test layout and conventions.

Archive
-------

- `Release history <https://call.report/library/ffiec-data-connect/release-history>`_ — version-by-version changes, 0.1.0 through 3.0.0rc2.

Source
------

- GitHub: `call-report/ffiec-data-connect <https://github.com/call-report/ffiec-data-connect>`_
- PyPI: `ffiec-data-connect <https://pypi.org/project/ffiec-data-connect/>`_
- Upstream ``CHANGELOG.md``: `github.com/call-report/ffiec-data-connect/blob/main/CHANGELOG.md <https://github.com/call-report/ffiec-data-connect/blob/main/CHANGELOG.md>`_
