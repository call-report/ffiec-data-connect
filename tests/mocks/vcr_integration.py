#!/usr/bin/env python3
"""
VCR.py integration for FFIEC Data Connect testing.

This module provides VCR.py integration for recording and replaying
HTTP/SOAP interactions with the real FFIEC web service.
"""

import os
import re
import json
import vcr
from typing import Dict, Any, Optional, List
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlparse


class FFIECVCRSanitizer:
    """Sanitizes sensitive data in VCR cassettes."""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = {
        'username': r'<UserID>([^<]+)</UserID>',
        'password': r'<Password>([^<]+)</Password>',
        'credentials': r'(username|password)(["\s]*[:=]["\s]*)([^"\'<>\s,}]+)',
        'auth_header': r'Authorization:\s*([^\r\n]+)',
        'session_id': r'JSESSIONID=([A-F0-9]+)',
        'cookies': r'Cookie:\s*([^\r\n]+)',
    }
    
    # Replacement values
    REPLACEMENTS = {
        'username': 'MOCK_USERNAME',
        'password': 'MOCK_PASSWORD', 
        'credentials': r'\1\2SANITIZED_VALUE',
        'auth_header': 'Authorization: SANITIZED_AUTH',
        'session_id': 'JSESSIONID=MOCK_SESSION_ID',
        'cookies': 'Cookie: SANITIZED_COOKIES',
    }
    
    @classmethod
    def sanitize_request(cls, request: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data in VCR request."""
        request = request.copy()
        
        # Sanitize body
        if 'body' in request and request['body']:
            if isinstance(request['body'], bytes):
                body_str = request['body'].decode('utf-8')
                body_str = cls._sanitize_text(body_str)
                request['body'] = body_str.encode('utf-8')
            elif isinstance(request['body'], str):
                request['body'] = cls._sanitize_text(request['body'])
        
        # Sanitize headers
        if 'headers' in request:
            request['headers'] = cls._sanitize_headers(request['headers'])
        
        return request
    
    @classmethod
    def sanitize_response(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data in VCR response."""
        response = response.copy()
        
        # Sanitize body
        if 'body' in response and response['body']:
            if isinstance(response['body'], bytes):
                body_str = response['body'].decode('utf-8')
                body_str = cls._sanitize_response_text(body_str)
                response['body'] = body_str.encode('utf-8')
            elif isinstance(response['body'], str):
                response['body'] = cls._sanitize_response_text(response['body'])
        
        # Sanitize headers
        if 'headers' in response:
            response['headers'] = cls._sanitize_headers(response['headers'])
        
        return response
    
    @classmethod
    def _sanitize_text(cls, text: str) -> str:
        """Sanitize sensitive data in text."""
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if pattern_name in cls.REPLACEMENTS:
                text = re.sub(pattern, cls.REPLACEMENTS[pattern_name], text, flags=re.IGNORECASE)
        
        return text
    
    @classmethod
    def _sanitize_response_text(cls, text: str) -> str:
        """Sanitize response-specific sensitive data."""
        # For now, responses typically don't contain credentials
        # But we can sanitize session IDs or other sensitive info
        for pattern_name in ['session_id']:
            if pattern_name in cls.SENSITIVE_PATTERNS and pattern_name in cls.REPLACEMENTS:
                pattern = cls.SENSITIVE_PATTERNS[pattern_name] 
                replacement = cls.REPLACEMENTS[pattern_name]
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    @classmethod
    def _sanitize_headers(cls, headers: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive headers."""
        sanitized_headers = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            
            if key_lower in ['authorization', 'cookie', 'set-cookie']:
                sanitized_headers[key] = 'SANITIZED_VALUE'
            elif isinstance(value, (list, tuple)):
                # Handle multi-value headers
                sanitized_values = []
                for v in value:
                    if key_lower in ['authorization', 'cookie', 'set-cookie']:
                        sanitized_values.append('SANITIZED_VALUE')
                    else:
                        sanitized_values.append(v)
                sanitized_headers[key] = sanitized_values
            else:
                sanitized_headers[key] = value
        
        return sanitized_headers


class FFIECVCRManager:
    """Manages VCR cassettes for FFIEC testing."""
    
    def __init__(self, cassette_dir: Optional[Path] = None):
        """Initialize VCR manager.
        
        Args:
            cassette_dir: Directory to store cassettes (default: tests/fixtures/vcr_cassettes)
        """
        if cassette_dir is None:
            cassette_dir = Path(__file__).parent.parent / "fixtures" / "vcr_cassettes"
        
        self.cassette_dir = Path(cassette_dir)
        self.cassette_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure VCR with sanitization
        self.vcr = vcr.VCR(
            cassette_library_dir=str(self.cassette_dir),
            record_mode='once',  # Record once, then replay
            match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
            filter_headers=['authorization', 'cookie', 'set-cookie'],
            before_record_request=self._before_record_request,
            before_record_response=self._before_record_response,
            serializer='json',
            custom_patches=[]
        )
    
    def _before_record_request(self, request):
        """Process request before recording."""
        # Apply sanitization
        sanitized = FFIECVCRSanitizer.sanitize_request({
            'body': request.body,
            'headers': dict(request.headers)
        })
        
        # Update request with sanitized data
        if 'body' in sanitized:
            request.body = sanitized['body']
        
        return request
    
    def _before_record_response(self, response):
        """Process response before recording.""" 
        # Apply sanitization
        sanitized = FFIECVCRSanitizer.sanitize_response({
            'body': response['body'],
            'headers': response.get('headers', {})
        })
        
        # Update response with sanitized data
        response['body'] = sanitized['body']
        
        return response
    
    def get_cassette(self, name: str, **kwargs) -> vcr.cassette.Cassette:
        """Get a VCR cassette for recording/playback.
        
        Args:
            name: Cassette name (without .json extension)
            **kwargs: Additional VCR options
        
        Returns:
            VCR cassette context manager
        """
        cassette_path = f"{name}.json"
        
        # Merge kwargs with default options
        options = {
            'record_mode': 'once',
            'match_on': ['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
        }
        options.update(kwargs)
        
        return self.vcr.use_cassette(cassette_path, **options)
    
    def create_test_cassette(
        self, 
        name: str,
        mock_responses: List[Dict[str, Any]],
        overwrite: bool = False
    ) -> Path:
        """Create a test cassette with mock responses.
        
        Args:
            name: Cassette name
            mock_responses: List of mock HTTP responses
            overwrite: Whether to overwrite existing cassette
        
        Returns:
            Path to created cassette file
        """
        cassette_path = self.cassette_dir / f"{name}.json"
        
        if cassette_path.exists() and not overwrite:
            raise FileExistsError(f"Cassette {cassette_path} already exists")
        
        # Create VCR-compatible cassette structure
        cassette_data = {
            "version": 1,
            "interactions": []
        }
        
        for response in mock_responses:
            interaction = {
                "request": {
                    "uri": response.get("uri", "http://localhost/mock"),
                    "method": response.get("method", "POST"),
                    "body": response.get("request_body", ""),
                    "headers": response.get("request_headers", {})
                },
                "response": {
                    "status": {"code": response.get("status_code", 200), "message": "OK"},
                    "headers": response.get("response_headers", {"content-type": ["text/xml"]}),
                    "body": {"string": response.get("response_body", "")},
                }
            }
            cassette_data["interactions"].append(interaction)
        
        # Write cassette file
        with open(cassette_path, 'w', encoding='utf-8') as f:
            json.dump(cassette_data, f, indent=2, ensure_ascii=False)
        
        return cassette_path
    
    def list_cassettes(self) -> List[Path]:
        """List all available cassettes."""
        return list(self.cassette_dir.glob("*.json"))
    
    def delete_cassette(self, name: str) -> bool:
        """Delete a cassette file.
        
        Args:
            name: Cassette name (with or without .json extension)
        
        Returns:
            True if deleted, False if not found
        """
        if not name.endswith('.json'):
            name = f"{name}.json"
        
        cassette_path = self.cassette_dir / name
        if cassette_path.exists():
            cassette_path.unlink()
            return True
        return False
    
    def validate_cassette(self, name: str) -> Dict[str, Any]:
        """Validate a cassette file and return info about it.
        
        Args:
            name: Cassette name
            
        Returns:
            Dictionary with validation results and cassette info
        """
        if not name.endswith('.json'):
            name = f"{name}.json"
        
        cassette_path = self.cassette_dir / name
        
        if not cassette_path.exists():
            return {"valid": False, "error": "Cassette file not found"}
        
        try:
            with open(cassette_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic validation
            if not isinstance(data, dict):
                return {"valid": False, "error": "Invalid cassette format"}
            
            if "interactions" not in data:
                return {"valid": False, "error": "No interactions found"}
            
            interactions = data["interactions"]
            if not isinstance(interactions, list):
                return {"valid": False, "error": "Invalid interactions format"}
            
            # Analyze interactions
            info = {
                "valid": True,
                "num_interactions": len(interactions),
                "methods": set(),
                "hosts": set(),
                "soap_actions": set(),
            }
            
            for interaction in interactions:
                if "request" in interaction:
                    req = interaction["request"]
                    info["methods"].add(req.get("method", "UNKNOWN"))
                    
                    uri = req.get("uri", "")
                    if uri:
                        parsed = urlparse(uri)
                        info["hosts"].add(parsed.hostname or "unknown")
                    
                    # Extract FFIEC SOAP actions from body
                    body = req.get("body", "")
                    if body and "<soap:" in body.lower():
                        try:
                            # Parse FFIEC SOAP actions
                            root = ET.fromstring(body)
                            namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                                        'ffiec': 'http://cdr.ffiec.gov/public/services'}
                            
                            for elem in root.iter():
                                if elem.tag.endswith('}Body') or elem.tag == 'Body':
                                    for child in elem:
                                        action = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                                        # Filter to known FFIEC operations
                                        if action in ['TestUserAccess', 'RetrieveReportingPeriods', 
                                                     'RetrievePanelOfReporters', 'RetrieveFacsimile',
                                                     'RetrieveUBPRReportingPeriods', 'RetrieveUBPRXBRLFacsimile',
                                                     'RetrieveFilersSubmissionDateTime', 'RetrieveFilersSinceDate']:
                                            info["soap_actions"].add(action)
                        except:
                            pass
            
            # Convert sets to lists for JSON serialization
            info["methods"] = list(info["methods"])
            info["hosts"] = list(info["hosts"])
            info["soap_actions"] = list(info["soap_actions"])
            
            return info
            
        except Exception as e:
            return {"valid": False, "error": f"Error reading cassette: {str(e)}"}


# Convenience functions for common testing patterns
def create_ffiec_vcr_manager(cassette_dir: Optional[Path] = None) -> FFIECVCRManager:
    """Create a VCR manager for FFIEC testing."""
    return FFIECVCRManager(cassette_dir)


def with_vcr_cassette(cassette_name: str, **vcr_kwargs):
    """Decorator for using VCR cassettes in tests."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            vcr_manager = create_ffiec_vcr_manager()
            with vcr_manager.get_cassette(cassette_name, **vcr_kwargs):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Example usage patterns for documentation
class FFIECVCRExamples:
    """Examples of VCR usage patterns for FFIEC testing."""
    
    @staticmethod
    def record_real_ffiec_response():
        """Example: Record a real FFIEC response."""
        # This would be used in a script to record actual responses
        vcr_manager = create_ffiec_vcr_manager()
        
        # Use in context manager to record
        with vcr_manager.get_cassette('real_data_response', record_mode='new_episodes'):
            # Make actual API call here - this would record it
            pass
    
    @staticmethod  
    def replay_recorded_response():
        """Example: Replay a recorded response in tests."""
        vcr_manager = create_ffiec_vcr_manager()
        
        # Use in playback mode (default)
        with vcr_manager.get_cassette('real_data_response'):
            # Make the same API call - it will be replayed from cassette
            pass
    
    @staticmethod
    def create_mock_cassette():
        """Example: Create a mock cassette for testing."""
        vcr_manager = create_ffiec_vcr_manager()
        
        mock_responses = [{
            "uri": "http://cdr.ffiec.gov/webservice",
            "method": "POST",
            "status_code": 200,
            "request_body": "<soap:Envelope>...</soap:Envelope>",
            "response_body": "<soap:Envelope><soap:Body>...</soap:Body></soap:Envelope>",
            "response_headers": {"content-type": ["text/xml; charset=utf-8"]}
        }]
        
        cassette_path = vcr_manager.create_test_cassette(
            'mock_banking_data',
            mock_responses
        )
        print(f"Created mock cassette: {cassette_path}")