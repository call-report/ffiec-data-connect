"""SOAP client caching - DEPRECATED.

The FFIEC SOAP API was shut down on February 28, 2026.
These functions are retained as no-op stubs for backward compatibility.
"""

import warnings
from typing import Any, Dict


def clear_soap_cache() -> None:
    """No-op stub. SOAP cache is no longer used."""
    warnings.warn(
        "clear_soap_cache() is a no-op. The FFIEC SOAP API was shut down on Feb 28, 2026. "
        "Use OAuth2Credentials with the REST API instead. "
        "See: https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx",
        DeprecationWarning,
        stacklevel=2,
    )


def get_cache_stats() -> Dict[str, Any]:
    """Returns empty stats. SOAP cache is no longer used."""
    warnings.warn(
        "get_cache_stats() returns empty data. The FFIEC SOAP API was shut down on Feb 28, 2026. "
        "Use OAuth2Credentials with the REST API instead. "
        "See: https://cdr.ffiec.gov/public/PWS/PublicLogin.aspx",
        DeprecationWarning,
        stacklevel=2,
    )
    return {"size": 0, "max_size": 0, "hit_ratio": 0.0, "keys": [], "deprecated": True}
