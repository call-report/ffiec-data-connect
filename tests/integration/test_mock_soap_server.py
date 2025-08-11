#!/usr/bin/env python3
"""
Integration test for the FFIEC mock SOAP server.

Tests that our mock server properly implements the real FFIEC SOAP operations
and returns schema-compliant responses.
"""

import time
import xml.etree.ElementTree as ET

import pytest
import requests

from tests.mocks.soap_server import MockFFIECServer


class TestMockFFIECServer:
    """Test the mock FFIEC SOAP server with real schema compliance."""

    def test_server_startup_shutdown(self):
        """Test server can start and stop properly."""
        server = MockFFIECServer(host="localhost", port=8089)

        # Test startup
        server.start()
        assert server.running is True
        assert server.url == "http://localhost:8089/webservice"

        # Test shutdown
        server.stop()
        assert server.running is False

    def test_wsdl_endpoint(self):
        """Test WSDL endpoint returns real FFIEC WSDL."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            response = requests.get(server.wsdl_url, timeout=5)

            assert response.status_code == 200
            assert response.headers["Content-Type"] == "text/xml; charset=utf-8"

            # Should contain FFIEC namespace and operations
            content = response.text
            assert "http://cdr.ffiec.gov/public/services" in content
            assert "RetrievalService" in content

    def test_test_user_access_operation(self):
        """Test TestUserAccess SOAP operation."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <TestUserAccess xmlns="http://cdr.ffiec.gov/public/services" />
    </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://cdr.ffiec.gov/public/services/TestUserAccess",
            }

            response = requests.post(
                server.url, data=soap_request, headers=headers, timeout=5
            )

            assert response.status_code == 200

            # Parse response to verify structure
            root = ET.fromstring(response.text)
            namespaces = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "ffiec": "http://cdr.ffiec.gov/public/services",
            }

            # Should contain TestUserAccessResult = true
            result = root.find(".//ffiec:TestUserAccessResult", namespaces)
            assert result is not None
            assert result.text == "true"

    def test_retrieve_reporting_periods_operation(self):
        """Test RetrieveReportingPeriods SOAP operation."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <RetrieveReportingPeriods xmlns="http://cdr.ffiec.gov/public/services">
            <dataSeries>Call</dataSeries>
        </RetrieveReportingPeriods>
    </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://cdr.ffiec.gov/public/services/RetrieveReportingPeriods",
            }

            response = requests.post(
                server.url, data=soap_request, headers=headers, timeout=5
            )

            assert response.status_code == 200

            # Parse response
            root = ET.fromstring(response.text)
            namespaces = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "ffiec": "http://cdr.ffiec.gov/public/services",
            }

            # Should contain period strings - they are in the FFIEC namespace
            periods = root.findall(".//ffiec:string", namespaces)
            assert len(periods) > 0

            # Should contain realistic quarter dates
            period_texts = [p.text for p in periods if p.text]
            assert any("2024" in p for p in period_texts)
            assert any("/31" in p for p in period_texts)  # Quarter end dates

    def test_retrieve_facsimile_operation(self):
        """Test RetrieveFacsimile SOAP operation with XBRL format."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <RetrieveFacsimile xmlns="http://cdr.ffiec.gov/public/services">
            <dataSeries>Call</dataSeries>
            <reportingPeriodEndDate>12/31/2023</reportingPeriodEndDate>
            <fiIDType>ID_RSSD</fiIDType>
            <fiID>480228</fiID>
            <facsimileFormat>XBRL</facsimileFormat>
        </RetrieveFacsimile>
    </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://cdr.ffiec.gov/public/services/RetrieveFacsimile",
            }

            response = requests.post(
                server.url, data=soap_request, headers=headers, timeout=5
            )

            assert response.status_code == 200

            # Parse response
            root = ET.fromstring(response.text)
            namespaces = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "ffiec": "http://cdr.ffiec.gov/public/services",
            }

            # Should contain base64-encoded XBRL result
            result = root.find(".//ffiec:RetrieveFacsimileResult", namespaces)
            assert result is not None
            assert result.text is not None
            assert len(result.text) > 0

            # Should be base64-encoded content
            import base64

            try:
                decoded = base64.b64decode(result.text)
                assert b"xbrl" in decoded.lower()
            except:
                pytest.fail("Result should be valid base64-encoded XBRL")

    def test_retrieve_ubpr_facsimile_operation(self):
        """Test RetrieveUBPRXBRLFacsimile SOAP operation."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <RetrieveUBPRXBRLFacsimile xmlns="http://cdr.ffiec.gov/public/services">
            <reportingPeriodEndDate>12/31/2023</reportingPeriodEndDate>
            <fiIDType>ID_RSSD</fiIDType>
            <fiID>480228</fiID>
        </RetrieveUBPRXBRLFacsimile>
    </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://cdr.ffiec.gov/public/services/RetrieveUBPRXBRLFacsimile",
            }

            response = requests.post(
                server.url, data=soap_request, headers=headers, timeout=5
            )

            assert response.status_code == 200

            # Parse response
            root = ET.fromstring(response.text)
            namespaces = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "ffiec": "http://cdr.ffiec.gov/public/services",
            }

            # Should contain base64-encoded UBPR XBRL result
            result = root.find(".//ffiec:RetrieveUBPRXBRLFacsimileResult", namespaces)
            assert result is not None
            assert result.text is not None
            assert len(result.text) > 0

    def test_server_call_history(self):
        """Test server call history tracking."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            # Clear history
            server.clear_call_history()

            # Make a test call
            soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <TestUserAccess xmlns="http://cdr.ffiec.gov/public/services" />
    </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://cdr.ffiec.gov/public/services/TestUserAccess",
            }

            response = requests.post(
                server.url, data=soap_request, headers=headers, timeout=5
            )
            assert response.status_code == 200

            # Check call history
            history = server.get_call_history()
            assert len(history) == 1

            call = history[0]
            assert call["method"] == "POST"
            assert call["path"] == "/webservice"
            assert "TestUserAccess" in call["body"]

    def test_error_handling(self):
        """Test server error handling for invalid requests."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            # Test invalid XML
            response = requests.post(server.url, data="invalid xml", timeout=5)
            assert response.status_code == 500

            # Should be a SOAP fault
            root = ET.fromstring(response.text)
            fault = root.find(
                ".//soap:Fault", {"soap": "http://schemas.xmlsoap.org/soap/envelope/"}
            )
            assert fault is not None

    def test_response_delay_configuration(self):
        """Test configurable response delays."""
        with MockFFIECServer(host="localhost", port=8089) as server:
            # Configure delay for TestUserAccess (no fi_id, so use empty string)
            server.configure_response_delay("TestUserAccess", "", 0.5)

            soap_request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <TestUserAccess xmlns="http://cdr.ffiec.gov/public/services" />
    </soap:Body>
</soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://cdr.ffiec.gov/public/services/TestUserAccess",
            }

            start_time = time.time()
            response = requests.post(
                server.url, data=soap_request, headers=headers, timeout=5
            )
            elapsed = time.time() - start_time

            assert response.status_code == 200
            assert elapsed >= 0.5  # Should have waited at least 500ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
