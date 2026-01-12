#!/usr/bin/env python3
"""
Test runner script for mcp_arena library verification.

This script runs comprehensive tests to verify the library is working correctly
before pushing to production.

Usage:
    python run_tests.py [--quick] [--communication] [--agents] [--installation]
    
Options:
    --quick: Run only fast unit tests
    --communication: Run only communication service tests
    --agents: Run only agent tests
    --installation: Run only installation tests
    --all: Run all tests (default)
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path


def run_command(cmd, timeout=300):
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def run_test_suite(test_type, test_args="", timeout=300):
    """Run a specific test suite."""
    print(f"\n{'='*60}")
    print(f"Running {test_type} tests...")
    print(f"{'='*60}")
    
    cmd = f"python -m pytest {test_args} -v --tb=short"
    print(f"Command: {cmd}")
    
    start_time = time.time()
    returncode, stdout, stderr = run_command(cmd, timeout)
    end_time = time.time()
    
    duration = end_time - start_time
    
    print(f"\n{test_type} Tests Results:")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Exit Code: {returncode}")
    
    if stdout:
        print("\nSTDOUT:")
        print(stdout)
    
    if stderr:
        print("\nSTDERR:")
        print(stderr)
    
    return returncode == 0, duration


def check_python_version():
    """Check Python version compatibility."""
    print("Checking Python version...")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("ERROR: Python 3.8+ required")
        return False
    
    print("OK Python version compatible")
    return True


def check_package_installation():
    """Check if mcp_arena package is installed."""
    print("\nChecking mcp_arena installation...")
    
    try:
        import mcp_arena
        print(f"OK mcp_arena version: {getattr(mcp_arena, '__version__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"ERROR: mcp_arena not installed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run mcp_arena test suite")
    parser.add_argument("--quick", action="store_true", help="Run only fast unit tests")
    parser.add_argument("--communication", action="store_true", help="Run only communication service tests")
    parser.add_argument("--agents", action="store_true", help="Run only agent tests")
    parser.add_argument("--installation", action="store_true", help="Run only installation tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific option provided
    if not any([args.quick, args.communication, args.agents, args.installation]):
        args.all = True
    
    print("mcp_arena Library Test Runner")
    print("=" * 60)
    
    # Basic checks
    if not check_python_version():
        sys.exit(1)
    
    if not check_package_installation():
        sys.exit(1)
    
    # Determine which tests to run
    test_suites = []
    total_duration = 0
    
    if args.all or args.installation:
        test_suites.append(("Installation", "tests/test_installation.py", 120))
    
    if args.all or args.quick:
        test_suites.append(("Import Tests", "tests/test_imports.py", 60))
    
    if args.all or args.communication:
        test_suites.append(("Communication Services", "tests/test_communication_services.py -m communication", 180))
    
    if args.all or args.agents:
        test_suites.append(("Agent Tests", "tests/test_agents.py -m agents", 120))
    
    if args.all:
        test_suites.append(("MCP Servers", "tests/test_mcp_servers.py -m unit", 180))
    
    if args.quick:
        test_suites.append(("Quick MCP Servers", "tests/test_mcp_servers.py::TestMCPServerInitialization::test_github_server_init", 60))
    
    # Run test suites
    results = []
    for test_name, test_args, timeout in test_suites:
        success, duration = run_test_suite(test_name, test_args, timeout)
        results.append((test_name, success))
        total_duration += duration
        
        if not success:
            print(f"\nWARNING: {test_name} tests failed!")
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Test Suites Run: {len(results)}")
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {status}: {test_name}")
    
    # Final verdict
    if failed == 0:
        print(f"\nAll tests passed! Library is ready for deployment.")
        return 0
    else:
        print(f"\n{failed} test suite(s) failed. Please fix issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
