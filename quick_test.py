#!/usr/bin/env python3
"""
Quick test runner for mcp_arena library verification.
Runs essential tests to verify the library is working correctly.
"""

import subprocess
import sys
import time


def run_test(test_name, test_command):
    """Run a single test and return success status."""
    print(f"\n{'='*50}")
    print(f"Running {test_name}")
    print(f"{'='*50}")
    
    start_time = time.time()
    try:
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Duration: {duration:.2f} seconds")
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout[-500:])  # Show last 500 chars
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr[-500:])  # Show last 500 chars
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Test timed out")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False


def main():
    """Run quick tests."""
    print("mcp_arena Quick Test Runner")
    print("=" * 50)
    
    tests = [
        ("Core Imports", "python -m pytest tests/test_imports.py::TestImports::test_core_imports -v"),
        ("Core Dependencies", "python -m pytest tests/test_imports.py::TestDependencies::test_core_dependencies -v"),
        ("Package Installation", "python -m pytest tests/test_installation.py::TestPackageInstallation::test_package_import -v"),
        ("Gmail Service", "python -m pytest tests/test_communication_services.py::TestGmailService::test_gmail_server_import -v"),
        ("Slack Service", "python -m pytest tests/test_communication_services.py::TestSlackService::test_slack_server_import -v"),
        ("Agent Initialization", "python -m pytest tests/test_agents.py::TestAgentInitialization::test_react_agent_init -v"),
        ("GitHub Server", "python -m pytest tests/test_mcp_servers.py::TestMCPServerInitialization::test_github_server_init -v"),
        ("CLI Tests", "python -m pytest tests/test_clis.py::TestCLI::test_list -v"),
        ("LangChain Integration", "python -m pytest tests/test_langchain_integration.py::TestMCPLangChainIntegration::test_init -v"),
    ]
    
    results = []
    total_duration = 0
    
    for test_name, test_command in tests:
        start_time = time.time()
        success = run_test(test_name, test_command)
        end_time = time.time()
        duration = end_time - start_time
        total_duration += duration
        
        results.append((test_name, success))
        
        if success:
            print(f"PASS: {test_name}")
        else:
            print(f"FAIL: {test_name}")
    
    # Summary
    print(f"\n{'='*50}")
    print("QUICK TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    print(f"Tests Run: {len(results)}")
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {status}: {test_name}")
    
    # Final verdict
    if failed == 0:
        print(f"\nAll quick tests passed! Library is ready for deployment.")
        return 0
    else:
        print(f"\n{failed} test(s) failed. Please fix issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
