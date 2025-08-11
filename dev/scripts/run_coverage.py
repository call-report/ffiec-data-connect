#!/usr/bin/env python3
"""
Comprehensive coverage reporting script for FFIEC Data Connect.

This script runs the test suite with coverage measurement and generates
multiple report formats for analysis.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

def run_command(cmd, timeout=300):
    """Run a command with timeout and error handling."""
    print(f"🏃 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after {timeout}s")
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return 1, "", str(e)

def main():
    parser = argparse.ArgumentParser(description="Run comprehensive coverage analysis")
    parser.add_argument("--fast", action="store_true", help="Run fast coverage (core modules only)")
    parser.add_argument("--full", action="store_true", help="Run full coverage (all modules)")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--xml", action="store_true", help="Generate XML report")
    parser.add_argument("--json", action="store_true", help="Generate JSON report")
    parser.add_argument("--fail-under", type=int, default=30, help="Minimum coverage percentage")
    args = parser.parse_args()

    # Set working directory to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("📊 FFIEC Data Connect - Comprehensive Coverage Analysis")
    print("=" * 60)
    
    # Clear previous coverage data
    print("🧹 Clearing previous coverage data...")
    run_command(["python", "-m", "coverage", "erase"])
    
    # Determine which tests to run
    if args.fast:
        test_modules = [
            "tests/unit/test_credentials.py",
            "tests/unit/test_ffiec_connection.py",
        ]
        print("🚀 Running FAST coverage (core modules)")
    elif args.full:
        test_modules = [
            "tests/unit/test_credentials.py",
            "tests/unit/test_ffiec_connection.py", 
            "tests/unit/test_methods.py",
            "tests/unit/test_async_compatible.py",
            "tests/unit/test_soap_cache.py",
            "tests/unit/test_thread_safety.py",
            "tests/unit/test_memory_leaks.py",
            "tests/unit/test_async_integration.py"
        ]
        print("🐌 Running FULL coverage (all modules - this will take time)")
    else:
        # Default: comprehensive but manageable
        test_modules = [
            "tests/unit/test_credentials.py",
            "tests/unit/test_ffiec_connection.py",
            "tests/unit/test_methods.py",
            "tests/unit/test_async_compatible.py",
            "tests/unit/test_soap_cache.py"
        ]
        print("⚖️  Running COMPREHENSIVE coverage (main modules)")
    
    print(f"📁 Test modules: {len(test_modules)}")
    
    # Run coverage
    start_time = time.time()
    
    cmd = [
        "python", "-m", "pytest", 
        *test_modules,
        "--cov=src/ffiec_data_connect",
        "--cov-config=.coveragerc",
        "--cov-report=term-missing",
        "--cov-branch",  # Include branch coverage
        "-x",  # Stop on first failure
        "--tb=short"  # Short traceback format
    ]
    
    # Add coverage failure threshold
    cmd.extend([f"--cov-fail-under={args.fail_under}"])
    
    returncode, stdout, stderr = run_command(cmd, timeout=600)  # 10 minute timeout
    
    elapsed = time.time() - start_time
    print(f"⏱️  Tests completed in {elapsed:.1f} seconds")
    
    if returncode != 0:
        print(f"❌ Tests failed with return code {returncode}")
        if stderr:
            print("STDERR:", stderr)
        if "FAIL Required test coverage" in stdout:
            print("📊 Coverage below threshold, but continuing with report generation...")
        else:
            print("❌ Test execution failed")
            return returncode
    else:
        print("✅ All tests passed!")
    
    # Print the coverage report that was already shown
    print("\n📊 Coverage Summary:")
    print("-" * 40)
    # The coverage report is already in stdout from pytest-cov
    
    # Generate additional reports if requested
    if args.html:
        print("\n🌐 Generating HTML coverage report...")
        returncode, stdout, stderr = run_command(["python", "-m", "coverage", "html"])
        if returncode == 0:
            print("✅ HTML report generated: htmlcov/index.html")
        else:
            print(f"❌ HTML report failed: {stderr}")
    
    if args.xml:
        print("\n📄 Generating XML coverage report...")
        returncode, stdout, stderr = run_command(["python", "-m", "coverage", "xml"])
        if returncode == 0:
            print("✅ XML report generated: coverage.xml")
        else:
            print(f"❌ XML report failed: {stderr}")
    
    if args.json:
        print("\n📋 Generating JSON coverage report...")
        returncode, stdout, stderr = run_command(["python", "-m", "coverage", "json"])
        if returncode == 0:
            print("✅ JSON report generated: coverage.json")
        else:
            print(f"❌ JSON report failed: {stderr}")
    
    # Coverage recommendations
    print("\n💡 Coverage Recommendations:")
    print("-" * 30)
    print("📈 Current coverage shows which modules need more tests:")
    print("   • Modules with <50% coverage need basic test coverage")
    print("   • Modules with 50-80% coverage need edge case testing")  
    print("   • Modules with >80% coverage are well tested")
    print("   • Focus on uncovered lines in the 'Missing' column")
    print("\n🎯 Next steps:")
    print("   1. Run with --html to see detailed line-by-line coverage")
    print("   2. Focus on critical modules (credentials, connection, methods)")
    print("   3. Add tests for error handling and edge cases")
    print("   4. Increase fail_under threshold gradually to 85%")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())