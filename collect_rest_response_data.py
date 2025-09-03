#!/usr/bin/env python3
"""
Comprehensive REST API Response Data Collection
Systematically test all 7 REST endpoints to document actual response structures
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, 'src')

from ffiec_data_connect import OAuth2Credentials
from ffiec_data_connect.protocol_adapter import create_protocol_adapter

class RESTResponseCollector:
    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token
        self.creds = OAuth2Credentials(
            username=username,
            bearer_token=token,
            token_expires=None
        )
        self.adapter = create_protocol_adapter(self.creds, None)
        self.results = {}
        self.request_count = 0
        
    def log_request(self, endpoint: str, params: dict = None, description: str = ""):
        """Log request details"""
        self.request_count += 1
        print(f"\n{'='*60}")
        print(f"REQUEST #{self.request_count}: {endpoint}")
        print(f"Description: {description}")
        if params:
            print(f"Parameters: {params}")
        print(f"Time: {datetime.now()}")
        print(f"{'='*60}")
        
    def log_response(self, endpoint: str, response_data, error=None):
        """Log and store response data"""
        result = {
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat(),
            'request_number': self.request_count,
            'success': error is None,
            'error': str(error) if error else None,
            'data_type': type(response_data).__name__ if response_data is not None else None,
            'data_length': len(response_data) if hasattr(response_data, '__len__') else None,
            'sample_data': None,
            'schema_info': {}
        }
        
        if error is None and response_data is not None:
            # Analyze response structure
            if isinstance(response_data, list):
                result['schema_info']['type'] = 'array'
                result['schema_info']['length'] = len(response_data)
                if len(response_data) > 0:
                    first_item = response_data[0]
                    result['schema_info']['item_type'] = type(first_item).__name__
                    if isinstance(first_item, dict):
                        result['schema_info']['item_keys'] = list(first_item.keys())
                        result['sample_data'] = first_item
                    else:
                        result['sample_data'] = first_item
                    
                    # Get additional samples
                    if len(response_data) > 1:
                        result['second_sample'] = response_data[1]
                    if len(response_data) > 2:
                        result['third_sample'] = response_data[2]
                        
            elif isinstance(response_data, dict):
                result['schema_info']['type'] = 'object'
                result['schema_info']['keys'] = list(response_data.keys())
                result['sample_data'] = response_data
            else:
                result['sample_data'] = response_data
        
        # Store result
        if endpoint not in self.results:
            self.results[endpoint] = []
        self.results[endpoint].append(result)
        
        # Print summary
        if error:
            print(f"❌ ERROR: {error}")
        else:
            print(f"✅ SUCCESS: {result['data_type']}")
            if result['data_length']:
                print(f"   Length: {result['data_length']}")
            if result['schema_info']:
                print(f"   Schema: {result['schema_info']}")
        
        # Rate limiting
        print("⏱️  Waiting 2 seconds (rate limiting)...")
        time.sleep(2)
        
    def save_results(self):
        """Save all results to JSON file"""
        output_file = Path("rest_api_response_data.json")
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n📁 Results saved to: {output_file}")
        return output_file
        
    def run_phase_1_metadata_endpoints(self):
        """Phase 1: Test metadata endpoints (4 requests)"""
        print(f"\n🔍 PHASE 1: METADATA ENDPOINTS")
        print(f"{'='*60}")
        
        # Test 1: RetrieveFilersSinceDate
        self.log_request(
            "RetrieveFilersSinceDate", 
            {"reporting_period": "12/31/2023", "since_date": "1/1/2023"},
            "Get RSSD IDs of filers since date - should return integer array"
        )
        try:
            response = self.adapter.retrieve_filers_since_date("12/31/2023", "1/1/2023")
            self.log_response("RetrieveFilersSinceDate", response)
        except Exception as e:
            self.log_response("RetrieveFilersSinceDate", None, e)
            
        # Test 2: RetrieveFilersSubmissionDateTime
        self.log_request(
            "RetrieveFilersSubmissionDateTime",
            {"reporting_period": "12/31/2023", "since_date": "1/1/2023"},
            "Get submission timestamps - should return array of {ID_RSSD, DateTime}"
        )
        try:
            response = self.adapter.retrieve_filers_submission_datetime("12/31/2023", "1/1/2023")
            self.log_response("RetrieveFilersSubmissionDateTime", response)
        except Exception as e:
            self.log_response("RetrieveFilersSubmissionDateTime", None, e)
            
        # Test 3: RetrieveUBPRReportingPeriods  
        self.log_request(
            "RetrieveUBPRReportingPeriods",
            {},
            "Get UBPR reporting periods - compare format with Call periods"
        )
        try:
            response = self.adapter.retrieve_ubpr_reporting_periods()
            self.log_response("RetrieveUBPRReportingPeriods", response)
        except Exception as e:
            self.log_response("RetrieveUBPRReportingPeriods", None, e)
            
        # Test 4: Error scenario
        self.log_request(
            "RetrievePanelOfReporters_ERROR",
            {"reporting_period": "invalid_date"},
            "Test error response structure with invalid date"
        )
        try:
            response = self.adapter.retrieve_panel_of_reporters("invalid_date")
            self.log_response("RetrievePanelOfReporters_ERROR", response)
        except Exception as e:
            self.log_response("RetrievePanelOfReporters_ERROR", None, e)
            
    def run_phase_2_facsimile_testing(self):
        """Phase 2: Test facsimile endpoints with different formats (15 requests)"""
        print(f"\n📄 PHASE 2: FACSIMILE FORMAT TESTING")
        print(f"{'='*60}")
        
        # Known good institutions for testing
        test_institutions = [
            {"rssd": "480228", "name": "JPMorgan Chase", "fdic_cert": "628"},
            {"rssd": "852218", "name": "Bank of America", "fdic_cert": "3510"},
        ]
        
        test_period = "12/31/2023"
        
        # Test XBRL format (3 requests)
        print(f"\n🔍 Testing XBRL Format...")
        for i, inst in enumerate(test_institutions[:2]):
            self.log_request(
                "RetrieveFacsimile_XBRL",
                {"rssd": inst["rssd"], "format": "XBRL", "period": test_period},
                f"XBRL for {inst['name']} - should return XML binary data"
            )
            try:
                response = self.adapter.retrieve_facsimile(inst["rssd"], test_period, "call")
                self.log_response("RetrieveFacsimile_XBRL", response)
            except Exception as e:
                self.log_response("RetrieveFacsimile_XBRL", None, e)
        
        # Test with FDICCertNumber as ID type
        self.log_request(
            "RetrieveFacsimile_XBRL_FDIC",
            {"fdic_cert": test_institutions[0]["fdic_cert"], "format": "XBRL"},
            "XBRL with FDICCertNumber ID type - test alternative ID"
        )
        try:
            # Note: This would require modifying the adapter to accept different ID types
            # For now, we'll test with RSSD and document the limitation
            response = self.adapter.retrieve_facsimile(test_institutions[0]["fdic_cert"], test_period, "call")
            self.log_response("RetrieveFacsimile_XBRL_FDIC", response)
        except Exception as e:
            self.log_response("RetrieveFacsimile_XBRL_FDIC", None, e)
            
        # Test error scenarios (3 requests)
        error_tests = [
            ("INVALID_RSSD", {"rssd": "999999999", "reason": "Invalid RSSD ID"}),
            ("INVALID_FORMAT", {"rssd": "480228", "reason": "Invalid format type"}),
            ("INVALID_PERIOD", {"rssd": "480228", "reason": "Invalid period"})
        ]
        
        for test_name, params in error_tests:
            self.log_request(
                f"RetrieveFacsimile_{test_name}",
                params,
                f"Error test: {params['reason']}"
            )
            try:
                if test_name == "INVALID_RSSD":
                    response = self.adapter.retrieve_facsimile(params["rssd"], test_period, "call")
                elif test_name == "INVALID_FORMAT":
                    # This would require modifying adapter to accept format parameter
                    response = self.adapter.retrieve_facsimile(params["rssd"], test_period, "call")
                elif test_name == "INVALID_PERIOD":
                    response = self.adapter.retrieve_facsimile(params["rssd"], "invalid/date", "call")
                self.log_response(f"RetrieveFacsimile_{test_name}", response)
            except Exception as e:
                self.log_response(f"RetrieveFacsimile_{test_name}", None, e)
                
    def run_phase_3_ubpr_testing(self):
        """Phase 3: Test UBPR facsimile endpoints (3 requests)"""
        print(f"\n📊 PHASE 3: UBPR FACSIMILE TESTING")
        print(f"{'='*60}")
        
        # Get a valid UBPR period first (from Phase 1 results)
        ubpr_periods = None
        if "RetrieveUBPRReportingPeriods" in self.results:
            for result in self.results["RetrieveUBPRReportingPeriods"]:
                if result["success"] and result.get("sample_data"):
                    ubpr_periods = result["sample_data"]
                    break
                    
        if ubpr_periods:
            test_period = ubpr_periods  # Use first available period
            
            self.log_request(
                "RetrieveUBPRXBRLFacsimile",
                {"rssd": "480228", "period": test_period},
                "UBPR XBRL for JPMorgan - compare with Call XBRL structure"
            )
            try:
                response = self.adapter.retrieve_ubpr_xbrl_facsimile("480228", test_period)
                self.log_response("RetrieveUBPRXBRLFacsimile", response)
            except Exception as e:
                self.log_response("RetrieveUBPRXBRLFacsimile", None, e)
                
            # Test with different RSSD
            self.log_request(
                "RetrieveUBPRXBRLFacsimile_Alt",
                {"rssd": "852218", "period": test_period},
                "UBPR XBRL for Bank of America"
            )
            try:
                response = self.adapter.retrieve_ubpr_xbrl_facsimile("852218", test_period)
                self.log_response("RetrieveUBPRXBRLFacsimile_Alt", response)
            except Exception as e:
                self.log_response("RetrieveUBPRXBRLFacsimile_Alt", None, e)
                
            # Error test
            self.log_request(
                "RetrieveUBPRXBRLFacsimile_Error",
                {"rssd": "999999999", "period": test_period},
                "UBPR error test with invalid RSSD"
            )
            try:
                response = self.adapter.retrieve_ubpr_xbrl_facsimile("999999999", test_period)
                self.log_response("RetrieveUBPRXBRLFacsimile_Error", response)
            except Exception as e:
                self.log_response("RetrieveUBPRXBRLFacsimile_Error", None, e)
        else:
            print("⚠️  Skipping UBPR tests - no valid periods found")
            
    def run_all_phases(self):
        """Run all data collection phases"""
        print(f"\n🚀 STARTING COMPREHENSIVE REST API DATA COLLECTION")
        print(f"User: {self.username}")
        print(f"Rate Limit: 2500 requests/hour")
        print(f"Expected Requests: ~25-30")
        print(f"Start Time: {datetime.now()}")
        
        try:
            self.run_phase_1_metadata_endpoints()
            self.run_phase_2_facsimile_testing()
            self.run_phase_3_ubpr_testing()
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Collection interrupted by user")
        except Exception as e:
            print(f"\n❌ Collection failed: {e}")
        finally:
            # Always save results
            output_file = self.save_results()
            
            print(f"\n📊 COLLECTION SUMMARY:")
            print(f"Total Requests: {self.request_count}")
            print(f"Endpoints Tested: {len(self.results)}")
            print(f"Results File: {output_file}")
            
            return self.results

def main():
    # Your credentials
    username = "cfs111"
    token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJBY2Nlc3MgVG9rZW4iLCJqdGkiOiI2ZTk2ZjBkZS03MjU1LTRhNTAtYjI0YS1hYmJjMjlmMWI3ODkiLCJuYmYiOjE3NTY4NDU3NDEsImV4cCI6MTc2NDYyNTM0MSwiaXNzIjoiMWVmYzAyYmMtMmRkYS00MWM4LWE4ZWItMjMxYTMzNDMzMDkzIiwiYXVkIjoiUFdTIFVzZXIifQ."
    
    collector = RESTResponseCollector(username, token)
    results = collector.run_all_phases()
    
    return results

if __name__ == "__main__":
    results = main()