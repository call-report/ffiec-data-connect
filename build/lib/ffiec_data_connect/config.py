"""
Configuration module for FFIEC Data Connect.

This module provides global configuration options including
backward compatibility settings.
"""

import os


class Config:
    """Global configuration for FFIEC Data Connect."""

    # Default to legacy behavior for backward compatibility
    _use_legacy_errors = os.environ.get("FFIEC_USE_LEGACY_ERRORS", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    _deprecation_warning_shown = False

    @classmethod
    def use_legacy_errors(cls) -> bool:
        """Check if legacy error mode is enabled.

        Returns:
            bool: True if legacy ValueError should be raised instead of specific exceptions
        """
        # Show deprecation warning once per session when using legacy mode
        if cls._use_legacy_errors and not cls._deprecation_warning_shown:
            import warnings

            warnings.warn(
                "Legacy error mode is deprecated and will be disabled by default in version 2.0.0. "
                "The new exception types provide better error context and debugging information. "
                "To migrate: catch specific exceptions (CredentialError, ValidationError, etc.) instead of ValueError. "
                "To disable this warning and opt into new behavior: set FFIEC_USE_LEGACY_ERRORS=false or call disable_legacy_mode().",
                DeprecationWarning,
                stacklevel=3,
            )
            cls._deprecation_warning_shown = True
        return cls._use_legacy_errors

    @classmethod
    def set_legacy_errors(cls, enabled: bool) -> None:
        """Set whether to use legacy error behavior.

        Args:
            enabled: True to raise ValueError for backward compatibility,
                    False to use new specific exception types
        """
        cls._use_legacy_errors = enabled

    @classmethod
    def reset(cls) -> None:
        """Reset configuration to defaults."""
        cls._use_legacy_errors = os.environ.get(
            "FFIEC_USE_LEGACY_ERRORS", "true"
        ).lower() in ("true", "1", "yes")
        cls._deprecation_warning_shown = False


# Convenience functions for module-level access
def use_legacy_errors() -> bool:
    """Check if legacy error mode is enabled."""
    return Config.use_legacy_errors()


def set_legacy_errors(enabled: bool) -> None:
    """Set whether to use legacy error behavior."""
    Config.set_legacy_errors(enabled)


def enable_legacy_mode() -> None:
    """Enable full legacy compatibility mode.

    This enables:
    - Legacy ValueError exceptions instead of specific exception types
    - Original error messages without additional context
    """
    Config.set_legacy_errors(True)


def disable_legacy_mode() -> None:
    """Disable legacy compatibility mode and use new features."""
    Config.set_legacy_errors(False)
