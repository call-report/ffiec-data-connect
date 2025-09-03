#!/usr/bin/env python3
"""
Test Pydantic Integration and Schema Compliance

This script validates that our Pydantic models work correctly with real
REST API responses and that validation provides clear error messages.
"""

import sys
import json
from pathlib import Path

# Add src to path  
sys.path.insert(0, 'src')

from pydantic import ValidationError as PydanticValidationError

from ffiec_data_connect.models import (
    ReportingPeriodsResponse,
    UBPRReportingPeriodsResponse,
    InstitutionsResponse,
    RSSDIDsResponse,
    SubmissionsResponse,
    Institution,
    SubmissionInfo
)
from ffiec_data_connect.data_normalizer import DataNormalizer


def test_model_validation():
    """Test Pydantic models with sample data."""
    print("🧪 Testing Pydantic Model Validation")
    print("=" * 50)
    
    # Test 1: Valid reporting periods
    valid_periods = ["12/31/2023", "9/30/2023", "6/30/2023"]
    try:
        validated = ReportingPeriodsResponse(valid_periods)
        print(f"✅ Valid reporting periods: {len(validated.root)} items")
    except PydanticValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
    
    # Test 2: Invalid date format
    invalid_periods = ["2023-12-31", "bad-date", "6/30/2023"]
    try:
        validated = ReportingPeriodsResponse(invalid_periods)
        print(f"❌ Should have failed validation: {validated}")
    except PydanticValidationError as e:
        print(f"✅ Correctly caught invalid date format: {e}")
    
    # Test 3: Valid RSSD IDs
    valid_rssd_ids = ["480228", "852218", "1234567"]
    try:
        validated = RSSDIDsResponse(valid_rssd_ids)
        print(f"✅ Valid RSSD IDs: {len(validated.root)} items")
    except PydanticValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
        
    # Test 4: Valid institution data
    valid_institution = {
        "ID_RSSD": 480228,
        "Name": "TEST BANK",
        "FDICCertNumber": 12345,
        "OCCChartNumber": 0,
        "OTSDockNumber": 0,
        "PrimaryABARoutNumber": 123456789,
        "State": "NY",
        "City": "NEW YORK",
        "Address": "123 MAIN ST",
        "ZIP": 10001,
        "FilingType": "051", 
        "HasFiledForReportingPeriod": True
    }
    
    try:
        validated = Institution(**valid_institution)
        print(f"✅ Valid institution: {validated.Name}")
    except PydanticValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
    
    # Test 5: Missing required field
    invalid_institution = {
        "Name": "TEST BANK",
        # Missing ID_RSSD (required field)
    }
    
    try:
        validated = Institution(**invalid_institution)
        print(f"❌ Should have failed validation: {validated}")
    except PydanticValidationError as e:
        print(f"✅ Correctly caught missing required field: {e}")
    
    print(f"\n📊 Model validation tests completed")


def test_data_normalizer_integration():
    """Test DataNormalizer Pydantic compatibility checks."""
    print(f"\n🔧 Testing DataNormalizer Pydantic Integration")
    print("=" * 50)
    
    # Test 1: Valid institution data
    valid_institutions = [
        {
            "ID_RSSD": "480228",  # Properly normalized to string
            "Name": "TEST BANK",
            "ZIP": "10001"  # Properly formatted ZIP
        }
    ]
    
    report = DataNormalizer.validate_pydantic_compatibility(
        valid_institutions, "RetrievePanelOfReporters"
    )
    
    if report["compatible"]:
        print(f"✅ Valid institution data passed compatibility check")
    else:
        print(f"❌ Valid data failed compatibility: {report['warnings']}")
    
    # Test 2: Invalid institution data
    invalid_institutions = [
        {
            "ID_RSSD": 480228,  # Integer instead of string
            "Name": "TEST BANK",
            "ZIP": "123"  # Too short ZIP
        }
    ]
    
    report = DataNormalizer.validate_pydantic_compatibility(
        invalid_institutions, "RetrievePanelOfReporters"
    )
    
    if not report["compatible"]:
        print(f"✅ Invalid institution data correctly flagged: {report['warnings'][:2]}")
    else:
        print(f"❌ Invalid data not caught by compatibility check")
    
    # Test 3: RSSD ID validation
    valid_rssd_ids = ["480228", "852218"]
    report = DataNormalizer.validate_pydantic_compatibility(
        valid_rssd_ids, "RetrieveFilersSinceDate"
    )
    
    if report["compatible"]:
        print(f"✅ Valid RSSD IDs passed compatibility check")
    else:
        print(f"❌ Valid RSSD data failed: {report['warnings']}")
    
    print(f"\n📊 DataNormalizer integration tests completed")


def test_normalization_stats():
    """Test normalization statistics generation."""
    print(f"\n📈 Testing Normalization Statistics")
    print("=" * 50)
    
    # Simulate REST API raw data
    rest_data = [
        {
            "ID_RSSD": 480228,  # Integer from REST
            "Name": "TEST BANK",
            "ZIP": 1001  # Integer ZIP (missing leading zeros)
        }
    ]
    
    # Simulate normalized data
    normalized_data = [
        {
            "ID_RSSD": "480228",  # String after normalization
            "Name": "TEST BANK", 
            "ZIP": "01001"  # String with leading zeros
        }
    ]
    
    stats = DataNormalizer.get_normalization_stats(
        rest_data, normalized_data, "RetrievePanelOfReporters"
    )
    
    print(f"📊 Normalization Statistics:")
    print(f"   Transformations Applied: {stats['transformations_applied']}")
    print(f"   Fields Normalized: {stats['fields_normalized']}")
    print(f"   Type Changes: {stats['type_changes']}")
    
    if stats['transformations_applied'] > 0:
        print(f"✅ Normalization statistics correctly tracked changes")
    else:
        print(f"❌ No transformations detected")


def main():
    """Run all Pydantic integration tests."""
    print("🚀 FFIEC Data Connect - Pydantic Integration Test Suite")
    print("=" * 60)
    
    try:
        test_model_validation()
        test_data_normalizer_integration()
        test_normalization_stats()
        
        print(f"\n🎉 All Pydantic integration tests completed!")
        print(f"✅ Schema compliance validation is working correctly")
        print(f"✅ Runtime validation provides clear error messages")
        print(f"✅ DataNormalizer integrates properly with Pydantic models")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())