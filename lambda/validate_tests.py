#!/usr/bin/env python3

import os
import sys
import subprocess

def main():
    """Simple test runner to validate the unit tests"""
    
    # Set up paths
    project_root = r"C:\mine\projects\vehicle-counting-system"
    lambda_dir = os.path.join(project_root, "lambda")
    
    print(f"Project root: {project_root}")
    print(f"Lambda directory: {lambda_dir}")
    
    # Check if directories exist
    if not os.path.exists(lambda_dir):
        print(f"ERROR: Lambda directory does not exist: {lambda_dir}")
        return False
    
    # Change to lambda directory
    os.chdir(lambda_dir)
    print(f"Changed to directory: {os.getcwd()}")
    
    # List test files
    test_dir = os.path.join(lambda_dir, "tests")
    if not os.path.exists(test_dir):
        print(f"ERROR: Tests directory does not exist: {test_dir}")
        return False
    
    test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
    print(f"Found test files: {test_files}")
    
    # Try to run a simple syntax check on test files
    print("\nChecking test file syntax...")
    for test_file in test_files:
        test_path = os.path.join(test_dir, test_file)
        try:
            # Use python -m py_compile to check syntax
            result = subprocess.run([sys.executable, "-m", "py_compile", test_path], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✓ {test_file}: Syntax OK")
            else:
                print(f"  ✗ {test_file}: Syntax Error")
                print(f"    {result.stderr}")
        except Exception as e:
            print(f"  ✗ {test_file}: Error checking syntax: {e}")
    
    # Try to run tests
    print(f"\nAttempting to run tests...")
    try:
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        print(f"Exit code: {result.returncode}")
        print("STDOUT:")
        print(result.stdout[:2000])  # Limit output
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr[:1000])  # Limit output
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Tests timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\nTest validation {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
