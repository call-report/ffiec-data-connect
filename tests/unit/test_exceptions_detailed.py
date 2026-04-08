"""Tests for ffiec_data_connect.exceptions — constructor and string behaviour."""

import pytest
from ffiec_data_connect.exceptions import (
    FFIECError,
    NoDataError,
    CredentialError,
    ConnectionError,
    RateLimitError,
    XMLParsingError,
    SessionError,
    SOAPDeprecationError,
)


class TestFFIECError:
    def test_str_without_details(self):
        err = FFIECError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.message == "something went wrong"
        assert err.details == {}

    def test_str_with_details(self):
        err = FFIECError("bad request", details={"code": 400})
        assert "bad request" in str(err)
        assert "Details:" in str(err)
        assert "400" in str(err)
        assert err.details == {"code": 400}

    def test_is_exception(self):
        err = FFIECError("test")
        assert isinstance(err, Exception)


class TestNoDataError:
    def test_without_params(self):
        err = NoDataError()
        assert "No data returned" in str(err)
        assert err.details == {}

    def test_with_rssd_id(self):
        err = NoDataError(rssd_id="480228")
        assert err.details["rssd_id"] == "480228"
        assert "Details:" in str(err)

    def test_with_reporting_period(self):
        err = NoDataError(reporting_period="03/31/2023")
        assert err.details["reporting_period"] == "03/31/2023"

    def test_with_both(self):
        err = NoDataError(rssd_id="480228", reporting_period="03/31/2023")
        assert err.details["rssd_id"] == "480228"
        assert err.details["reporting_period"] == "03/31/2023"


class TestCredentialError:
    def test_without_credential_source(self):
        err = CredentialError("invalid token")
        assert str(err) == "invalid token"
        assert err.details == {}

    def test_with_credential_source(self):
        err = CredentialError("invalid token", credential_source="environment")
        assert err.details["credential_source"] == "environment"
        assert "Details:" in str(err)


class TestConnectionError:
    def test_without_optional_args(self):
        err = ConnectionError("timeout")
        assert str(err) == "timeout"
        assert err.details == {}

    def test_with_url(self):
        err = ConnectionError("timeout", url="https://example.com/api")
        assert err.details["url"] == "https://example.com/api"

    def test_with_status_code(self):
        err = ConnectionError("server error", status_code=500)
        assert err.details["status_code"] == 500

    def test_with_url_and_status_code(self):
        err = ConnectionError("fail", url="https://x.com", status_code=503)
        assert err.details["url"] == "https://x.com"
        assert err.details["status_code"] == 503
        assert "Details:" in str(err)


class TestRateLimitError:
    def test_without_retry_after(self):
        err = RateLimitError()
        assert "rate limit exceeded" in str(err)
        assert err.details == {}

    def test_with_retry_after(self):
        err = RateLimitError(retry_after=60)
        assert "Retry after 60 seconds" in str(err)
        assert err.details["retry_after_seconds"] == 60


class TestXMLParsingError:
    def test_without_snippet(self):
        err = XMLParsingError("parse failed")
        assert str(err) == "parse failed"
        assert err.details == {}

    def test_with_short_snippet(self):
        snippet = "<root><child/></root>"
        err = XMLParsingError("parse failed", xml_snippet=snippet)
        assert err.details["xml_snippet"] == snippet

    def test_with_long_snippet_truncated(self):
        snippet = "x" * 300
        err = XMLParsingError("parse failed", xml_snippet=snippet)
        stored = err.details["xml_snippet"]
        assert len(stored) == 203  # 200 chars + "..."
        assert stored.endswith("...")
        assert stored[:200] == "x" * 200


class TestSessionError:
    def test_without_session_state(self):
        err = SessionError("expired")
        assert str(err) == "expired"
        assert err.details == {}

    def test_with_session_state(self):
        err = SessionError("expired", session_state="timed_out")
        assert err.details["session_state"] == "timed_out"
        assert "Details:" in str(err)


class TestSOAPDeprecationError:
    def test_attributes(self):
        err = SOAPDeprecationError(
            soap_method="RetrieveFacsimile",
            rest_equivalent="GET /api/facsimile",
            code_example='ffiec.get_facsimile(rssd_id="480228")',
        )
        assert err.soap_method == "RetrieveFacsimile"
        assert err.rest_equivalent == "GET /api/facsimile"
        assert err.code_example == 'ffiec.get_facsimile(rssd_id="480228")'

    def test_message_contains_soap_method(self):
        err = SOAPDeprecationError(
            soap_method="RetrieveFacsimile",
            rest_equivalent="GET /api/facsimile",
            code_example="example()",
        )
        assert "RetrieveFacsimile" in str(err)

    def test_message_contains_rest_equivalent(self):
        err = SOAPDeprecationError(
            soap_method="RetrieveFacsimile",
            rest_equivalent="GET /api/facsimile",
            code_example="example()",
        )
        assert "GET /api/facsimile" in str(err)

    def test_message_contains_code_example(self):
        err = SOAPDeprecationError(
            soap_method="RetrieveFacsimile",
            rest_equivalent="GET /api/facsimile",
            code_example='ffiec.get_facsimile(rssd_id="480228")',
        )
        assert 'ffiec.get_facsimile(rssd_id="480228")' in str(err)

    def test_details_dict(self):
        err = SOAPDeprecationError(
            soap_method="RetrieveFacsimile",
            rest_equivalent="GET /api/facsimile",
            code_example="example()",
        )
        assert err.details["soap_method"] == "RetrieveFacsimile"
        assert err.details["rest_equivalent"] == "GET /api/facsimile"

    def test_message_mentions_shutdown_date(self):
        err = SOAPDeprecationError(
            soap_method="X",
            rest_equivalent="Y",
            code_example="Z",
        )
        assert "February 28, 2026" in str(err)

    def test_is_ffiec_error(self):
        err = SOAPDeprecationError(
            soap_method="X",
            rest_equivalent="Y",
            code_example="Z",
        )
        assert isinstance(err, FFIECError)
        assert isinstance(err, Exception)
