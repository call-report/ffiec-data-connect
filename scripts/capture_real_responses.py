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
            
            # Save reporting periods
            periods_file = self.output_dir / "reporting_periods.json"
            with open(periods_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "periods": periods,
                    "count": len(periods),
                    "source": "FFIEC CDR"
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
            Dictionary of captured responses (real public FFIEC data)
        """
        captured_data = {}
        
        # Use recent periods (last 4 quarters)
        recent_periods = sorted(periods, reverse=True)[:4]
        print(f"📊 Capturing data for periods: {recent_periods}")
        print(f"🏦 Sample banks: {sample_rssds}")
        
        for period in recent_periods:
            period_data = {}
            
            for rssd_id in sample_rssds:
                bank_data = {}
                
                # Collect both Call Report and UBPR data for comprehensive fixtures
                for series in ["call", "ubpr"]:
                    try:
                        print(f"  Fetching {rssd_id} ({series.upper()}) for {period}...")
                        
                        # Add delay to respect rate limits
                        time.sleep(1)
                        
                        data = collect_data(
                            session=self.connection.session,
                            creds=self.credentials,
                            reporting_period=period,
                            rssd_id=rssd_id,
                            series=series,
                            output_type="list"  # Keep as list to preserve original structure
                        )
                        
                        if data:
                            bank_data[series] = data
                            print(f"    ✅ Got {len(data)} {series.upper()} data points")
                        else:
                            print(f"    ⚠️  No {series.upper()} data returned")
                            bank_data[series] = []
                            
                    except Exception as e:
                        print(f"    ❌ {series.upper()} failed: {e}")
                        bank_data[series] = {"error": str(e)}
                
                # Store both series for this bank
                period_data[rssd_id] = bank_data
            
            captured_data[period] = period_data
        
        return captured_data
    
    def save_fixtures(self, real_data: Dict[str, Any]) -> None:
        """Save real FFIEC data as test fixtures."""
        
        # Save complete fixture with real public data
        fixture_file = self.output_dir / "real_ffiec_data.json"
        with open(fixture_file, 'w') as f:
            json.dump({
                "metadata": {
                    "generated": datetime.now().isoformat(),
                    "description": "Real FFIEC bank data for testing",
                    "note": "Authentic public banking data from FFIEC webservice",
                    "data_source": "FFIEC Central Data Repository"
                },
                "data": real_data
            }, f, indent=2)
        
        print(f"💾 Saved complete fixture: {fixture_file}")
        
        # Save individual period fixtures for targeted testing
        for period, period_data in real_data.items():
            period_file = self.output_dir / f"period_{period.replace('-', '_')}.json"
            with open(period_file, 'w') as f:
                json.dump({
                    "period": period,
                    "banks": period_data,
                    "generated": datetime.now().isoformat(),
                    "source": "FFIEC CDR"
                }, f, indent=2)
        
        print(f"💾 Saved {len(real_data)} individual period fixtures")
    
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
        
        sample_file = self.output_dir / "sample_responses.json"
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
        
        # Save fixtures (no sanitization needed - data is public)
        print("💾 Saving test fixtures...")
        capture.save_fixtures(raw_data)
        
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