#!/usr/bin/env python3
"""
FFIEC Real Response Capture Script

This script captures real responses from the FFIEC webservice for testing purposes.
It sanitizes sensitive data and creates test fixtures that can be used for 
integration testing without requiring live FFIEC credentials.

Usage:
    python capture_real_responses.py --help
    python capture_real_responses.py --username YOUR_USER --password YOUR_PASS
    
Environment variables:
    FFIEC_USERNAME - FFIEC webservice username
    FFIEC_PASSWORD - FFIEC webservice password (security token)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import hashlib
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ffiec_data_connect import WebserviceCredentials, FFIECConnection
    from ffiec_data_connect import collect_reporting_periods, collect_data
    from ffiec_data_connect.exceptions import FFIECError
except ImportError as e:
    print(f"❌ Failed to import ffiec_data_connect: {e}")
    print("Make sure you're running this from the project root and the package is installed:")
    print("  pip install -e .")
    sys.exit(1)


class ResponseCapture:
    """Captures and sanitizes FFIEC webservice responses."""
    
    def __init__(self, username: str, password: str, output_dir: str = "tests/fixtures"):
        """Initialize the response capture system.
        
        Args:
            username: FFIEC webservice username
            password: FFIEC webservice password/token
            output_dir: Directory to save captured responses
        """
        self.credentials = WebserviceCredentials(username, password)
        self.connection = FFIECConnection()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "raw").mkdir(exist_ok=True)
        (self.output_dir / "sanitized").mkdir(exist_ok=True)
        (self.output_dir / "vcr_cassettes").mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir.absolute()}")
    
    def test_connection(self) -> bool:
        """Test connection to FFIEC webservice."""
        try:
            print("🔐 Testing FFIEC connection...")
            self.credentials.test_credentials(self.connection.session)
            print("✅ Connection successful!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def capture_reporting_periods(self) -> Optional[List[str]]:
        """Capture available reporting periods."""
        try:
            print("📅 Capturing reporting periods...")
            periods = collect_reporting_periods(
                self.connection.session,
                self.credentials,
                output_type="list"
            )
            
            # Save raw response
            raw_file = self.output_dir / "raw" / "reporting_periods.json"
            with open(raw_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "periods": periods,
                    "count": len(periods)
                }, f, indent=2)
            
            print(f"✅ Captured {len(periods)} reporting periods")
            return periods
            
        except Exception as e:
            print(f"❌ Failed to capture reporting periods: {e}")
            return None
    
    def capture_sample_bank_data(self, periods: List[str], sample_rssds: List[str]) -> Dict[str, Any]:
        """Capture sample bank data for testing.
        
        Args:
            periods: List of reporting periods to capture
            sample_rssds: List of RSSD IDs to capture data for
        
        Returns:
            Dictionary of captured responses
        """
        captured_data = {}
        
        # Use recent periods (last 4 quarters)
        recent_periods = sorted(periods, reverse=True)[:4]
        print(f"📊 Capturing data for periods: {recent_periods}")
        print(f"🏦 Sample banks: {sample_rssds}")
        
        for period in recent_periods:
            period_data = {}
            
            for rssd_id in sample_rssds:
                try:
                    print(f"  Fetching {rssd_id} for {period}...")
                    
                    # Add delay to respect rate limits
                    time.sleep(1)
                    
                    data = collect_data(
                        session=self.connection.session,
                        creds=self.credentials,
                        rssd_id=rssd_id,
                        reporting_period=period,
                        output_type="dict"
                    )
                    
                    if data:
                        period_data[rssd_id] = data
                        print(f"    ✅ Got {len(data)} data points")
                    else:
                        print(f"    ⚠️  No data returned")
                        
                except Exception as e:
                    print(f"    ❌ Failed: {e}")
                    period_data[rssd_id] = {"error": str(e)}
            
            captured_data[period] = period_data
        
        return captured_data
    
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize captured data to remove sensitive information.
        
        Args:
            data: Raw captured data
            
        Returns:
            Sanitized data safe for test fixtures
        """
        sanitized = {}
        
        for period, period_data in data.items():
            sanitized_period = {}
            
            for rssd_id, bank_data in period_data.items():
                if isinstance(bank_data, dict) and "error" not in bank_data:
                    sanitized_bank = self._sanitize_bank_data(bank_data, rssd_id)
                    sanitized_period[rssd_id] = sanitized_bank
                else:
                    # Keep error data as-is for testing error scenarios
                    sanitized_period[rssd_id] = bank_data
            
            sanitized[period] = sanitized_period
        
        return sanitized
    
    def _sanitize_bank_data(self, bank_data: List[Dict], original_rssd: str) -> List[Dict]:
        """Sanitize individual bank data records."""
        sanitized_records = []
        
        for record in bank_data:
            sanitized_record = record.copy()
            
            # Replace actual RSSD with consistent test RSSD
            test_rssd = self._generate_test_rssd(original_rssd)
            if 'rssd' in sanitized_record:
                sanitized_record['rssd'] = test_rssd
            
            # Scramble actual financial values while preserving data types and structure
            if 'int_data' in sanitized_record and sanitized_record['int_data'] is not None:
                sanitized_record['int_data'] = self._scramble_numeric_value(
                    sanitized_record['int_data'], is_int=True
                )
            
            if 'float_data' in sanitized_record and sanitized_record['float_data'] is not None:
                sanitized_record['float_data'] = self._scramble_numeric_value(
                    sanitized_record['float_data'], is_int=False
                )
            
            # Keep MDRM codes and structure intact (not sensitive)
            # Keep quarters and dates intact (public information)
            
            sanitized_records.append(sanitized_record)
        
        return sanitized_records
    
    def _generate_test_rssd(self, original_rssd: str) -> str:
        """Generate consistent test RSSD ID from original."""
        # Create deterministic but different RSSD for testing
        hash_obj = hashlib.md5(f"test_{original_rssd}".encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert to 8-digit number (typical RSSD format)
        test_number = int(hash_hex[:8], 16) % 99999999 + 10000000
        return str(test_number)
    
    def _scramble_numeric_value(self, value: float, is_int: bool = False) -> float:
        """Scramble numeric value while preserving magnitude and type."""
        if value == 0:
            return 0
        
        # Preserve sign and rough magnitude
        sign = 1 if value >= 0 else -1
        abs_value = abs(value)
        
        # Get magnitude (power of 10)
        magnitude = len(str(int(abs_value))) if abs_value >= 1 else 0
        
        # Create scrambled value of similar magnitude
        hash_input = f"scramble_{value}_{magnitude}".encode()
        hash_obj = hashlib.md5(hash_input)
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Create value of similar magnitude
        if magnitude > 0:
            scrambled = hash_int % (10 ** magnitude)
            if scrambled == 0:
                scrambled = 10 ** (magnitude - 1)
        else:
            scrambled = hash_int % 1000 + 1  # Small positive number
        
        result = sign * scrambled
        return int(result) if is_int else float(result)
    
    def save_fixtures(self, sanitized_data: Dict[str, Any]) -> None:
        """Save sanitized data as test fixtures."""
        
        # Save complete fixture
        fixture_file = self.output_dir / "sanitized" / "sample_bank_data.json"
        with open(fixture_file, 'w') as f:
            json.dump({
                "metadata": {
                    "generated": datetime.now().isoformat(),
                    "description": "Sanitized FFIEC bank data for testing",
                    "note": "All sensitive data has been scrambled while preserving structure"
                },
                "data": sanitized_data
            }, f, indent=2)
        
        print(f"💾 Saved complete fixture: {fixture_file}")
        
        # Save individual period fixtures for targeted testing
        for period, period_data in sanitized_data.items():
            period_file = self.output_dir / "sanitized" / f"period_{period.replace('-', '_')}.json"
            with open(period_file, 'w') as f:
                json.dump({
                    "period": period,
                    "banks": period_data,
                    "generated": datetime.now().isoformat()
                }, f, indent=2)
        
        print(f"💾 Saved {len(sanitized_data)} individual period fixtures")
    
    def create_sample_responses(self) -> Dict[str, Any]:
        """Create sample response structures for different scenarios."""
        samples = {
            "empty_response": [],
            "single_record": [
                {
                    "mdrm": "RCON0010",
                    "rssd": "12345678",
                    "quarter": "2023-12-31",
                    "data_type": "int",
                    "int_data": 1500000000,
                    "float_data": None,
                    "bool_data": None,
                    "str_data": None
                }
            ],
            "mixed_data_types": [
                {
                    "mdrm": "RCON0010",
                    "rssd": "12345678", 
                    "quarter": "2023-12-31",
                    "data_type": "int",
                    "int_data": 1500000000,
                    "float_data": None,
                    "bool_data": None,
                    "str_data": None
                },
                {
                    "mdrm": "UBPR4107",
                    "rssd": "12345678",
                    "quarter": "2023-12-31", 
                    "data_type": "float",
                    "int_data": None,
                    "float_data": 12.54,
                    "bool_data": None,
                    "str_data": None
                },
                {
                    "mdrm": "TEXTITEM",
                    "rssd": "12345678",
                    "quarter": "2023-12-31",
                    "data_type": "str", 
                    "int_data": None,
                    "float_data": None,
                    "bool_data": None,
                    "str_data": "Sample Text"
                }
            ]
        }
        
        sample_file = self.output_dir / "sanitized" / "sample_responses.json"
        with open(sample_file, 'w') as f:
            json.dump({
                "metadata": {
                    "description": "Sample response structures for different test scenarios",
                    "generated": datetime.now().isoformat()
                },
                "samples": samples
            }, f, indent=2)
        
        print(f"💾 Created sample response fixtures: {sample_file}")
        return samples


def main():
    """Main entry point for the response capture script."""
    parser = argparse.ArgumentParser(
        description="Capture real FFIEC webservice responses for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python capture_real_responses.py --username myuser --password mytoken
    python capture_real_responses.py --output-dir custom/fixtures
    
    # Using environment variables
    export FFIEC_USERNAME=myuser
    export FFIEC_PASSWORD=mytoken
    python capture_real_responses.py
        """
    )
    
    parser.add_argument(
        "--username", "-u",
        help="FFIEC webservice username (or set FFIEC_USERNAME env var)"
    )
    parser.add_argument(
        "--password", "-p", 
        help="FFIEC webservice password/token (or set FFIEC_PASSWORD env var)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="tests/fixtures",
        help="Output directory for fixtures (default: tests/fixtures)"
    )
    parser.add_argument(
        "--sample-banks", "-b",
        nargs="+",
        default=["480228", "852320", "628403"],  # Sample large, medium, small banks
        help="RSSD IDs of sample banks to capture (default: 3 sample banks)"
    )
    parser.add_argument(
        "--max-periods", "-m",
        type=int,
        default=4,
        help="Maximum number of recent periods to capture (default: 4)"
    )
    parser.add_argument(
        "--test-connection-only",
        action="store_true",
        help="Only test connection, don't capture data"
    )
    
    args = parser.parse_args()
    
    # Get credentials from args or environment
    username = args.username or os.getenv("FFIEC_USERNAME")
    password = args.password or os.getenv("FFIEC_PASSWORD")
    
    if not username or not password:
        print("❌ Error: FFIEC credentials required")
        print("   Provide via --username/--password or FFIEC_USERNAME/FFIEC_PASSWORD environment variables")
        sys.exit(1)
    
    print("🚀 Starting FFIEC Response Capture")
    print(f"   Username: {username}")
    print(f"   Output: {args.output_dir}")
    
    try:
        capture = ResponseCapture(username, password, args.output_dir)
        
        # Test connection
        if not capture.test_connection():
            sys.exit(1)
        
        if args.test_connection_only:
            print("✅ Connection test successful. Exiting.")
            return
        
        # Capture reporting periods
        periods = capture.capture_reporting_periods()
        if not periods:
            print("❌ Failed to capture reporting periods")
            sys.exit(1)
        
        # Create sample responses first (doesn't require API calls)
        print("📝 Creating sample response fixtures...")
        capture.create_sample_responses()
        
        # Capture sample bank data
        print("📊 Capturing sample bank data...")
        print("   ⚠️  This may take several minutes due to API rate limits...")
        
        raw_data = capture.capture_sample_bank_data(periods, args.sample_banks)
        
        # Sanitize data
        print("🔒 Sanitizing captured data...")
        sanitized_data = capture.sanitize_data(raw_data)
        
        # Save fixtures
        print("💾 Saving test fixtures...")
        capture.save_fixtures(sanitized_data)
        
        print("✅ Response capture completed successfully!")
        print(f"   Fixtures saved to: {capture.output_dir.absolute()}")
        print("   Use these fixtures for integration testing without requiring live credentials.")
        
    except KeyboardInterrupt:
        print("\n⚠️  Capture interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Capture failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()