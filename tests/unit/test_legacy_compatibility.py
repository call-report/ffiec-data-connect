"""
Test legacy error compatibility mode.

Ensures backward compatibility for users expecting ValueError exceptions.
"""

import os
from unittest.mock import patch

import pytest

from ffiec_data_connect import (
    CredentialError,
    ValidationError,
    WebserviceCredentials,
    disable_legacy_mode,
    enable_legacy_mode,
    set_legacy_errors,
    use_legacy_errors,
)
from ffiec_data_connect.methods import _validate_rssd_id


class TestLegacyErrorMode:
    """Test legacy error compatibility."""

    def teardown_method(self):
        """Reset to default after each test."""
        from ffiec_data_connect.config import Config

        Config.reset()

    def test_legacy_mode_default_enabled(self):
        """Test that legacy mode is enabled by default for backward compatibility."""
        # Reset to ensure we get default behavior
        from ffiec_data_connect.config import Config

        Config.reset()
        assert use_legacy_errors() is True

    def test_enable_legacy_mode(self):
        """Test enabling legacy mode."""
        enable_legacy_mode()
        assert use_legacy_errors() is True

        disable_legacy_mode()
        assert use_legacy_errors() is False

    def test_set_legacy_errors(self):
        """Test setting legacy errors flag."""
        set_legacy_errors(True)
        assert use_legacy_errors() is True

        set_legacy_errors(False)
        assert use_legacy_errors() is False

    def test_environment_variable(self):
        """Test that environment variable controls default."""
        # Save original env
        original = os.environ.get("FFIEC_USE_LEGACY_ERRORS")

        try:
            # Test disabling via env var (since default is now true)
            os.environ["FFIEC_USE_LEGACY_ERRORS"] = "false"
            # Need to reload config module to pick up env change
            from ffiec_data_connect.config import Config

            Config.reset()
            assert use_legacy_errors() is False

            # Test enabling via env var
            os.environ["FFIEC_USE_LEGACY_ERRORS"] = "true"
            Config.reset()
            assert use_legacy_errors() is True

            # Test other truthy values
            for value in ["1", "yes", "YES", "True", "TRUE"]:
                os.environ["FFIEC_USE_LEGACY_ERRORS"] = value
                Config.reset()
                assert use_legacy_errors() is True

            # Test other falsy values
            for value in ["0", "no", "NO", "False", "FALSE"]:
                os.environ["FFIEC_USE_LEGACY_ERRORS"] = value
                Config.reset()
                assert use_legacy_errors() is False

        finally:
            # Restore original env
            if original is None:
                os.environ.pop("FFIEC_USE_LEGACY_ERRORS", None)
            else:
                os.environ["FFIEC_USE_LEGACY_ERRORS"] = original
            from ffiec_data_connect.config import Config

            Config.reset()

    def test_credentials_error_legacy_mode(self):
        """Test that credentials errors raise ValueError in legacy mode."""
        enable_legacy_mode()

        # Should raise ValueError instead of CredentialError
        with pytest.raises(ValueError) as exc_info:
            WebserviceCredentials()  # No credentials

        # Check it's ValueError, not CredentialError
        assert type(exc_info.value) is ValueError
        assert "Missing required credentials" in str(exc_info.value)

        # Disable legacy mode
        disable_legacy_mode()

        # Now should raise CredentialError
        with pytest.raises(CredentialError) as exc_info:
            WebserviceCredentials()

        assert type(exc_info.value) is CredentialError
        assert "Missing required credentials" in str(exc_info.value)

    def test_validation_error_legacy_mode(self):
        """Test that validation errors raise ValueError in legacy mode."""
        enable_legacy_mode()

        # Should raise ValueError for invalid RSSD
        with pytest.raises(ValueError) as exc_info:
            _validate_rssd_id("abc123")

        assert type(exc_info.value) is ValueError
        assert "RSSD ID must be numeric" in str(exc_info.value)

        # Disable legacy mode
        disable_legacy_mode()

        # Now should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            _validate_rssd_id("abc123")

        assert type(exc_info.value) is ValidationError
        assert "numeric" in str(exc_info.value)

    def test_all_error_types_legacy_mode(self):
        """Test that all error types work in legacy mode."""
        from ffiec_data_connect.exceptions import (
            ConnectionError,
            NoDataError,
            RateLimitError,
            SessionError,
            XMLParsingError,
            raise_exception,
        )

        enable_legacy_mode()

        # Test each error type raises ValueError in legacy mode
        # Note: Different exceptions have different constructors
        error_tests = [
            (
                SessionError,
                "Session error",
                "Session error occurred",
                {"session_state": "test"},
            ),
            (
                ConnectionError,
                "Connection failed",
                "Connection failed to server",
                {"url": "http://test"},
            ),
            (XMLParsingError, "XML parse error", "Failed to parse XML", {}),
            (
                RateLimitError,
                "Rate limit exceeded",
                None,
                {"retry_after": 60},
            ),  # Special case - no message arg
            (
                NoDataError,
                "No data found",
                None,
                {"rssd_id": "12345"},
            ),  # Special case - no message arg
        ]

        for error_class, legacy_msg, new_msg, kwargs in error_tests:
            with pytest.raises(ValueError) as exc_info:
                if new_msg is None:
                    # For RateLimitError and NoDataError that don't take message
                    raise_exception(error_class, legacy_msg, **kwargs)
                else:
                    raise_exception(error_class, legacy_msg, new_msg, **kwargs)

            assert type(exc_info.value) is ValueError
            assert legacy_msg in str(exc_info.value)

        # Disable legacy mode and test specific exceptions
        disable_legacy_mode()

        for error_class, legacy_msg, new_msg, kwargs in error_tests:
            with pytest.raises(error_class) as exc_info:
                if new_msg is None:
                    # For RateLimitError and NoDataError that don't take message
                    raise_exception(error_class, legacy_msg, **kwargs)
                else:
                    raise_exception(error_class, legacy_msg, new_msg, **kwargs)

            assert type(exc_info.value) is error_class

    def test_legacy_mode_thread_local(self):
        """Test that legacy mode setting is global, not thread-local."""
        import threading

        results = []

        def check_legacy_mode():
            results.append(use_legacy_errors())

        # Enable legacy mode in main thread
        enable_legacy_mode()

        # Check in another thread
        thread = threading.Thread(target=check_legacy_mode)
        thread.start()
        thread.join()

        # Should be True in other thread too (global setting)
        assert results[0] is True

        disable_legacy_mode()

    def test_deprecation_warning_shown(self):
        """Test that deprecation warning is shown when using legacy mode."""
        import warnings

        from ffiec_data_connect.config import Config

        # Reset to ensure warning can be shown
        Config.reset()
        Config._deprecation_warning_shown = False

        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Trigger the warning by checking legacy mode
            assert use_legacy_errors() is True

            # Should have a deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "Legacy error mode is deprecated" in str(w[0].message)
            assert "version 1.0.0" in str(w[0].message)

        # Warning should only be shown once
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assert use_legacy_errors() is True
            # No new warning
            assert len(w) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
