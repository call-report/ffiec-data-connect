"""
Tests for deprecated SOAP cache stubs.

Verifies that the remaining stub functions emit DeprecationWarning
and that removed classes are no longer importable.
"""

import pytest


class TestSoapCacheStubs:
    """Test deprecated SOAP cache stub functions."""

    def test_clear_soap_cache_emits_deprecation_warning(self):
        from ffiec_data_connect.soap_cache import clear_soap_cache

        with pytest.warns(DeprecationWarning):
            clear_soap_cache()

    def test_get_cache_stats_emits_deprecation_warning(self):
        from ffiec_data_connect.soap_cache import get_cache_stats

        with pytest.warns(DeprecationWarning):
            result = get_cache_stats()

    def test_get_cache_stats_returns_expected_dict(self):
        from ffiec_data_connect.soap_cache import get_cache_stats

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = get_cache_stats()

        assert result == {
            "size": 0,
            "max_size": 0,
            "hit_ratio": 0.0,
            "keys": [],
            "deprecated": True,
        }

    def test_old_imports_raise_import_error(self):
        with pytest.raises(ImportError):
            from ffiec_data_connect.soap_cache import SOAPClientConfig

        with pytest.raises(ImportError):
            from ffiec_data_connect.soap_cache import SOAPClientCache

        with pytest.raises(ImportError):
            from ffiec_data_connect.soap_cache import get_soap_client
