#!/usr/bin/env python3
"""Test runner script for S3 Bucket Scanner"""
import subprocess
import sys
import os


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running S3 Bucket Scanner Tests")
    print("=" * 60)
    
    # Change to the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Install test dependencies
    print("\nInstalling test dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "tests/requirements.txt"], check=True)
    
    # Run tests with coverage
    print("\nRunning tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80"
    ], cwd=project_dir)
    
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    print("=" * 60)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
