#!/usr/bin/env python3
"""
Mock SOAP server for FFIEC Data Connect testing.

This module provides a comprehensive mock SOAP server that simulates
the FFIEC web service for testing purposes.
"""

import json
import threading
import time
from typing import Dict, List, Optional, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


class FFIECMockSOAPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock FFIEC SOAP service."""
    
    # Mock data store
    mock_responses: Dict[str, Any] = {}
    call_history: List[Dict[str, Any]] = []
    response_delays: Dict[str, float] = {}
    error_responses: Dict[str, str] = {}
    
    def do_POST(self):
        """Handle POST requests (SOAP calls)."""
        try:
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Log the call
            self._log_request(post_data)
            
            # Try to parse SOAP request - this will fail for invalid XML
            try:
                soap_action = self._extract_soap_action(post_data)
                parameters = self._extract_parameters(post_data)
            except Exception:
                # Invalid XML or malformed SOAP
                self._send_error_response("Invalid SOAP request")
                return
            
            # Check for configured error responses
            error_key = f"{soap_action}_{parameters.get('fi_id', '')}"
            if error_key in self.error_responses:
                self._send_error_response(self.error_responses[error_key])
                return
            
            # Add configured delay - check both fi_id and rssd_id patterns
            delay_key = f"{soap_action}_{parameters.get('fi_id', '')}"
            alt_delay_key = f"{soap_action}_"
            if delay_key in self.response_delays:
                time.sleep(self.response_delays[delay_key])
            elif alt_delay_key in self.response_delays:
                time.sleep(self.response_delays[alt_delay_key])
            
            # Generate response based on real FFIEC SOAP operations
            if soap_action == "TestUserAccess":
                response = self._generate_test_user_access_response(parameters)
            elif soap_action == "RetrieveReportingPeriods":
                response = self._generate_retrieve_reporting_periods_response(parameters)
            elif soap_action == "RetrievePanelOfReporters":
                response = self._generate_retrieve_panel_response(parameters)
            elif soap_action == "RetrieveFacsimile":
                response = self._generate_retrieve_facsimile_response(parameters)
            elif soap_action == "RetrieveUBPRReportingPeriods":
                response = self._generate_ubpr_reporting_periods_response(parameters)
            elif soap_action == "RetrieveUBPRXBRLFacsimile":
                response = self._generate_ubpr_facsimile_response(parameters)
            elif soap_action == "RetrieveFilersSubmissionDateTime":
                response = self._generate_filers_submission_datetime_response(parameters)
            elif soap_action == "RetrieveFilersSinceDate":
                response = self._generate_filers_since_date_response(parameters)
            else:
                response = self._generate_generic_response(soap_action, parameters)
            
            # Send response
            self._send_soap_response(response)
            
        except Exception as e:
            self._send_error_response(f"Internal server error: {str(e)}")
    
    def do_GET(self):
        """Handle GET requests (for WSDL)."""
        if self.path.endswith('?wsdl') or self.path.endswith('.wsdl'):
            self._send_wsdl_response()
        else:
            self._send_404()
    
    def _log_request(self, post_data: str) -> None:
        """Log the SOAP request for analysis."""
        self.call_history.append({
            'timestamp': datetime.now().isoformat(),
            'method': self.command,
            'path': self.path,
            'headers': dict(self.headers),
            'body': post_data,
            'client': self.client_address[0]
        })
    
    def _extract_soap_action(self, soap_request: str) -> str:
        """Extract SOAP action from the request."""
        # Look for SOAPAction header first (FFIEC uses this)
        soap_action = self.headers.get('SOAPAction', '').strip('"')
        if soap_action:
            # FFIEC actions are like "http://cdr.ffiec.gov/public/services/RetrieveFacsimile"
            return soap_action.split('/')[-1] if '/' in soap_action else soap_action
        
        # Parse XML to find the action in SOAP body
        # This will raise an exception for invalid XML
        root = ET.fromstring(soap_request)
        
        # Look for FFIEC namespace elements
        namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                     'ffiec': 'http://cdr.ffiec.gov/public/services'}
        
        # Find the first element in the Body
        for elem in root.iter():
            if elem.tag.endswith('}Body') or elem.tag == 'Body':
                for child in elem:
                    tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    return tag_name
        
        return "UnknownAction"
    
    def _extract_parameters(self, soap_request: str) -> Dict[str, str]:
        """Extract parameters from FFIEC SOAP request."""
        params = {}
        try:
            root = ET.fromstring(soap_request)
            
            # FFIEC-specific parameter mappings based on real WSDL
            param_mappings = {
                'dataSeries': 'data_series',
                'reportingPeriodEndDate': 'reporting_period_end_date', 
                'fiIDType': 'fi_id_type',
                'fiID': 'fi_id',
                'facsimileFormat': 'facsimile_format',
                'sinceDate': 'since_date'
            }
            
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name in param_mappings and elem.text:
                    params[param_mappings[tag_name]] = elem.text
                elif elem.text and not elem.text.isspace() and len(elem.text.strip()) > 0:
                    # Capture any other parameters with original names
                    params[tag_name] = elem.text.strip()
                    
        except Exception:
            pass
        
        return params
    
    def _generate_test_user_access_response(self, params: Dict[str, str]) -> str:
        """Generate TestUserAccess response (returns boolean)."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <TestUserAccessResponse xmlns="http://cdr.ffiec.gov/public/services">
            <TestUserAccessResult>true</TestUserAccessResult>
        </TestUserAccessResponse>
    </soap:Body>
</soap:Envelope>"""

    def _generate_retrieve_panel_response(self, params: Dict[str, str]) -> str:
        """Generate RetrievePanelOfReporters response matching FFIEC schema."""
        data_series = params.get('data_series', 'Call')
        reporting_period = params.get('reporting_period_end_date', '2023-12-31')
        
        # Mock realistic panel data based on series  
        reporters_xml = ""
        if data_series == 'Call':
            sample_reporters = [
                {"ID_RSSD": "480228", "Name": "JPMorgan Chase Bank, National Association", "City": "Columbus", "State": "OH", "FDIC_Cert": "628", "Filing_Status": "Filed"},
                {"ID_RSSD": "852320", "Name": "Bank of America, National Association", "City": "Charlotte", "State": "NC", "FDIC_Cert": "3510", "Filing_Status": "Filed"},
                {"ID_RSSD": "628403", "Name": "Wells Fargo Bank, National Association", "City": "Sioux Falls", "State": "SD", "FDIC_Cert": "451", "Filing_Status": "Filed"}
            ]
        else:
            sample_reporters = [
                {"ID_RSSD": "480228", "Name": "JPMorgan Chase Bank, National Association", "City": "Columbus", "State": "OH", "FDIC_Cert": "628", "Filing_Status": "Filed"},
                {"ID_RSSD": "852320", "Name": "Bank of America, National Association", "City": "Charlotte", "State": "NC", "FDIC_Cert": "3510", "Filing_Status": "Filed"}
            ]
        
        for reporter in sample_reporters:
            reporters_xml += f"""
                <ReportingInstitution>
                    <ID_RSSD>{reporter['ID_RSSD']}</ID_RSSD>
                    <InstitutionName>{reporter['Name']}</InstitutionName>
                    <MainOfficeCity>{reporter['City']}</MainOfficeCity>
                    <MainOfficeState>{reporter['State']}</MainOfficeState>
                    <FDICCertNumber>{reporter['FDIC_Cert']}</FDICCertNumber>
                    <FilingStatus>{reporter['Filing_Status']}</FilingStatus>
                </ReportingInstitution>"""
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <RetrievePanelOfReportersResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrievePanelOfReportersResult>
                <PanelOfReporters>
                    {reporters_xml}
                </PanelOfReporters>
            </RetrievePanelOfReportersResult>
        </RetrievePanelOfReportersResponse>
    </soap:Body>
</soap:Envelope>"""
    
    def _generate_retrieve_reporting_periods_response(self, params: Dict[str, str]) -> str:
        """Generate RetrieveReportingPeriods response matching FFIEC schema."""
        data_series = params.get('data_series', 'Call')
        
        # Generate realistic reporting periods
        periods = []
        
        if data_series == 'Call':
            # Call Report quarterly periods (last 10 quarters)
            base_quarters = [
                "12/31/2024", "9/30/2024", "6/30/2024", "3/31/2024",
                "12/31/2023", "9/30/2023", "6/30/2023", "3/31/2023", 
                "12/31/2022", "9/30/2022", "6/30/2022", "3/31/2022",
                "12/31/2021", "9/30/2021"
            ]
            periods = base_quarters[:10]
        
        periods_xml = ""
        for period in periods:
            periods_xml += f"<string>{period}</string>"
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <RetrieveReportingPeriodsResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrieveReportingPeriodsResult xmlns:a="http://cdr.ffiec.gov/public/services">
                {periods_xml}
            </RetrieveReportingPeriodsResult>
        </RetrieveReportingPeriodsResponse>
    </soap:Body>
</soap:Envelope>"""

    def _generate_ubpr_reporting_periods_response(self, params: Dict[str, str]) -> str:
        """Generate RetrieveUBPRReportingPeriods response matching FFIEC schema."""
        # UBPR periods (quarterly)
        ubpr_periods = [
            "12/31/2024", "9/30/2024", "6/30/2024", "3/31/2024", 
            "12/31/2023", "9/30/2023", "6/30/2023", "3/31/2023",
            "12/31/2022", "9/30/2022"
        ]
        
        periods_xml = ""
        for period in ubpr_periods:
            periods_xml += f"<string>{period}</string>"
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <RetrieveUBPRReportingPeriodsResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrieveUBPRReportingPeriodsResult>
                {periods_xml}
            </RetrieveUBPRReportingPeriodsResult>
        </RetrieveUBPRReportingPeriodsResponse>
    </soap:Body>
</soap:Envelope>"""
    
    def _generate_retrieve_facsimile_response(self, params: Dict[str, str]) -> str:
        """Generate RetrieveFacsimile response with base64-encoded XBRL data."""
        fi_id = params.get('fi_id', '480228')
        data_series = params.get('data_series', 'Call')
        reporting_period = params.get('reporting_period_end_date', '2023-12-31')
        facsimile_format = params.get('facsimile_format', 'XBRL')
        
        # Mock base64-encoded XBRL content (simplified for testing)
        # In reality, this would be a full XBRL document encoded in base64
        mock_xbrl_content = """PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHhicmwgeG1sbnM9Imh0dHA6Ly93d3cueGJybC5vcmcvMjAwMy9pbnN0YW5jZSI+CiAgPGNvbnRleHQgaWQ9ImN0eF8yMDIzXzEyXzMxIj4KICAgIDxlbnRpdHk+CiAgICAgIDxpZGVudGlmaWVyIHNjaGVtZT0iaHR0cDovL2ZmaWVjLmdvdi9yc3NkIj40ODAyMjg8L2lkZW50aWZpZXI+CiAgICA8L2VudGl0eT4KICAgIDxwZXJpb2Q+CiAgICAgIDxpbnN0YW50PjIwMjMtMTItMzE8L2luc3RhbnQ+CiAgICA8L3BlcmlvZD4KICA8L2NvbnRleHQ+CiAgPHVuaXQgaWQ9InVzZCI+CiAgICA8bWVhc3VyZT5pc280MjE3OlVTRDwvbWVhc3VyZT4KICA8L3VuaXQ+CiAgPGNhbGw6VG90YWxBc3NldHMgY29udGV4dFJlZj0iY3R4XzIwMjNfMTJfMzEiIHVuaXRSZWY9InVzZCIgZGVjaW1hbHM9Ii0zIj4zNDU2MDAwMDAwPC9jYWxsOlRvdGFsQXNzZXRzPgo8L3hicmw+"""
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <RetrieveFacsimileResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrieveFacsimileResult>{mock_xbrl_content}</RetrieveFacsimileResult>
        </RetrieveFacsimileResponse>
    </soap:Body>
</soap:Envelope>"""

    def _generate_ubpr_facsimile_response(self, params: Dict[str, str]) -> str:
        """Generate RetrieveUBPRXBRLFacsimile response with base64-encoded XBRL data."""
        fi_id = params.get('fi_id', '480228')
        reporting_period = params.get('reporting_period_end_date', '2023-12-31')
        
        # Mock base64-encoded UBPR XBRL content 
        mock_ubpr_xbrl = """PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHhicmwgeG1sbnM9Imh0dHA6Ly93d3cueGJybC5vcmcvMjAwMy9pbnN0YW5jZSI+CiAgPGNvbnRleHQgaWQ9ImN0eF8yMDIzXzEyXzMxIj4KICAgIDxlbnRpdHk+CiAgICAgIDxpZGVudGlmaWVyIHNjaGVtZT0iaHR0cDovL2ZmaWVjLmdvdi9yc3NkIj40ODAyMjg8L2lkZW50aWZpZXI+CiAgICA8L2VudGl0eT4KICA8L2NvbnRleHQ+CiAgPHVicHI6UmV0dXJuT25Bc3NldHMgY29udGV4dFJlZj0iY3R4XzIwMjNfMTJfMzEiPjEuMjU8L3VicHI6UmV0dXJuT25Bc3NldHM+CiAgPHVicHI6TmV0SW50ZXJlc3RNYXJnaW4gY29udGV4dFJlZj0iY3R4XzIwMjNfMTJfMzEiPjMuNDI8L3VicHI6TmV0SW50ZXJlc3RNYXJnaW4+CjwveGJybD4="""
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <RetrieveUBPRXBRLFacsimileResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrieveUBPRXBRLFacsimileResult>{mock_ubpr_xbrl}</RetrieveUBPRXBRLFacsimileResult>
        </RetrieveUBPRXBRLFacsimileResponse>
    </soap:Body>
</soap:Envelope>"""

    def _generate_filers_submission_datetime_response(self, params: Dict[str, str]) -> str:
        """Generate RetrieveFilersSubmissionDateTime response."""
        # Mock submission datetime data
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <RetrieveFilersSubmissionDateTimeResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrieveFilersSubmissionDateTimeResult>
                <string>480228,2023-12-31,2024-01-15T10:30:00</string>
                <string>852320,2023-12-31,2024-01-18T14:45:00</string>
                <string>628403,2023-12-31,2024-01-20T09:15:00</string>
            </RetrieveFilersSubmissionDateTimeResult>
        </RetrieveFilersSubmissionDateTimeResponse>
    </soap:Body>
</soap:Envelope>"""

    def _generate_filers_since_date_response(self, params: Dict[str, str]) -> str:
        """Generate RetrieveFilersSinceDate response."""
        since_date = params.get('since_date', '2024-01-01')
        
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <RetrieveFilersSinceDateResponse xmlns="http://cdr.ffiec.gov/public/services">
            <RetrieveFilersSinceDateResult>
                <string>480228</string>
                <string>852320</string>
                <string>628403</string>
            </RetrieveFilersSinceDateResult>
        </RetrieveFilersSinceDateResponse>
    </soap:Body>
</soap:Envelope>"""

    
    def _generate_generic_response(self, action: str, params: Dict[str, str]) -> str:
        """Generate a generic SOAP response for unknown actions."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <{action}Response>
            <{action}Result>
                <Status>Success</Status>
                <Message>Mock response for {action}</Message>
                <Parameters>{json.dumps(params)}</Parameters>
            </{action}Result>
        </{action}Response>
    </soap:Body>
</soap:Envelope>"""
    
    def _send_soap_response(self, response_body: str) -> None:
        """Send a SOAP response."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(response_body.encode('utf-8'))))
        self.send_header('SOAPAction', '""')
        self.end_headers()
        self.wfile.write(response_body.encode('utf-8'))
    
    def _send_error_response(self, error_message: str) -> None:
        """Send a SOAP fault response."""
        fault_response = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <soap:Fault>
            <faultcode>Server</faultcode>
            <faultstring>{error_message}</faultstring>
            <detail>
                <ErrorCode>MOCK_ERROR</ErrorCode>
                <Timestamp>{datetime.now().isoformat()}</Timestamp>
            </detail>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>"""
        
        self.send_response(500)
        self.send_header('Content-Type', 'text/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(fault_response.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(fault_response.encode('utf-8'))
    
    def _send_wsdl_response(self) -> None:
        """Send the real FFIEC WSDL response."""
        try:
            # Try to read the real FFIEC WSDL we downloaded
            wsdl_path = Path(__file__).parent.parent / "fixtures" / "wsdl_samples" / "ffiec_real_retrieval_service.wsdl"
            if wsdl_path.exists():
                with open(wsdl_path, 'r', encoding='utf-8') as f:
                    wsdl_content = f.read()
                    # Update the service location to point to our mock server
                    wsdl_content = wsdl_content.replace(
                        'https://cdr.ffiec.gov/public/pws/webservices/retrievalservice.asmx',
                        f'http://{self.server.server_name}:{self.server.server_port}/webservice'
                    )
            else:
                # Fallback minimal WSDL
                wsdl_content = """<?xml version="1.0" encoding="utf-8"?>
<wsdl:definitions xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/" 
                  xmlns:tns="http://cdr.ffiec.gov/public/services"
                  targetNamespace="http://cdr.ffiec.gov/public/services">
    <wsdl:service name="RetrievalService">
        <wsdl:port name="RetrievalServiceSoap" binding="tns:RetrievalServiceSoap">
            <soap:address location="http://localhost:8089/webservice"/>
        </wsdl:port>
    </wsdl:service>
</wsdl:definitions>"""
        except Exception:
            wsdl_content = "<!-- WSDL Error -->"
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(wsdl_content.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(wsdl_content.encode('utf-8'))
    
    def _send_404(self) -> None:
        """Send a 404 Not Found response."""
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def log_message(self, format_str, *args):
        """Override to suppress default logging."""
        pass  # Suppress default HTTP server logging


class MockFFIECServer:
    """Mock FFIEC SOAP server for testing."""
    
    def __init__(self, host: str = 'localhost', port: int = 8089):
        """Initialize the mock server.
        
        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
    
    def start(self) -> None:
        """Start the mock server in a background thread."""
        if self.running:
            return
        
        self.server = HTTPServer((self.host, self.port), FFIECMockSOAPHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        self.running = True
        
        # Wait a moment for server to start
        time.sleep(0.1)
    
    def stop(self) -> None:
        """Stop the mock server."""
        if not self.running or not self.server:
            return
        
        self.server.shutdown()
        self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1.0)
        
        self.running = False
        self.server = None
        self.thread = None
    
    def configure_response_delay(self, action: str, rssd_id: str, delay: float) -> None:
        """Configure a response delay for specific requests.
        
        Args:
            action: SOAP action name
            rssd_id: RSSD ID for the request (can be empty string for general delays)
            delay: Delay in seconds
        """
        key = f"{action}_{rssd_id}"
        FFIECMockSOAPHandler.response_delays[key] = delay
    
    def configure_error_response(self, action: str, rssd_id: str, error_message: str) -> None:
        """Configure an error response for specific requests.
        
        Args:
            action: SOAP action name  
            rssd_id: RSSD ID for the request
            error_message: Error message to return
        """
        key = f"{action}_{rssd_id}"
        FFIECMockSOAPHandler.error_responses[key] = error_message
    
    def clear_configurations(self) -> None:
        """Clear all response configurations."""
        FFIECMockSOAPHandler.response_delays.clear()
        FFIECMockSOAPHandler.error_responses.clear()
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get the history of all SOAP calls made to the server."""
        return FFIECMockSOAPHandler.call_history.copy()
    
    def clear_call_history(self) -> None:
        """Clear the call history."""
        FFIECMockSOAPHandler.call_history.clear()
    
    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}/webservice"
    
    @property
    def wsdl_url(self) -> str:
        """Get the WSDL URL."""
        return f"{self.url}?wsdl"
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()