"""
Unit tests for ffiec_connection.py after SOAP deprecation.

FFIECConnection.__init__() now raises SOAPDeprecationError immediately.
The class shell remains for isinstance compatibility. These tests verify
the deprecation behaviour and that supporting types are still importable.
"""

import pytest

from ffiec_data_connect.exceptions import SOAPDeprecationError
from ffiec_data_connect.ffiec_connection import FFIECConnection, ProxyProtocol


class TestFFIECConnectionRaisesDeprecation:
    """All attempts to instantiate FFIECConnection must raise SOAPDeprecationError."""

    def test_instantiation_raises_soap_deprecation_error(self):
        """FFIECConnection() raises SOAPDeprecationError."""
        with pytest.raises(SOAPDeprecationError):
            FFIECConnection()

    def test_error_message_mentions_session_none(self):
        """The migration guidance tells the user to pass session=None."""
        with pytest.raises(SOAPDeprecationError, match=r"session=None"):
            FFIECConnection()

    def test_error_message_mentions_oauth2_credentials(self):
        """The migration guidance mentions OAuth2Credentials."""
        with pytest.raises(SOAPDeprecationError, match=r"OAuth2Credentials"):
            FFIECConnection()

    def test_error_attributes(self):
        """The raised exception carries structured migration metadata."""
        with pytest.raises(SOAPDeprecationError) as exc_info:
            FFIECConnection()

        err = exc_info.value
        assert err.soap_method == "FFIECConnection"
        assert "session=None" in err.rest_equivalent


class TestImportability:
    """Verify that the module's public names are still importable."""

    def test_ffiec_connection_importable(self):
        """FFIECConnection class is importable (isinstance compatibility)."""
        assert FFIECConnection is not None

    def test_proxy_protocol_enum_importable(self):
        """ProxyProtocol enum is still importable and has expected members."""
        assert ProxyProtocol.HTTP.value == 0
        assert ProxyProtocol.HTTPS.value == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
