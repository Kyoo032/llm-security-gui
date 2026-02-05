#!/usr/bin/env python3
"""
Test script for HuggingFace authentication fixes
Run this to verify all authentication methods work correctly
"""

import os
import sys

# Add color output for better visibility
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_failure(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

print_header("HuggingFace Authentication Test Suite")

# Test 1: Import huggingface_hub
print_header("Test 1: Import huggingface_hub")
try:
    from huggingface_hub import get_token as hf_get_token
    print_success("Successfully imported huggingface_hub.get_token")
    import huggingface_hub
    print_info(f"Version: {huggingface_hub.__version__}")
except ImportError as e:
    print_failure(f"Failed to import huggingface_hub: {e}")
    print_warning("Fix: pip install -U 'huggingface_hub[cli]'")
    sys.exit(1)

# Test 2: Check token detection methods
print_header("Test 2: Token Detection Methods")

# Method 1: get_token()
print(f"\n{Colors.BOLD}Method 1: huggingface_hub.get_token(){Colors.RESET}")
try:
    token = hf_get_token()
    if token:
        print_success(f"Token found (length: {len(token)} characters)")
        print_info(f"Starts with: {token[:10]}...")
    else:
        print_warning("No token found via get_token()")
        print_info("This is expected if not logged in")
except Exception as e:
    print_failure(f"Error calling get_token(): {e}")

# Method 2: Direct file reading
print(f"\n{Colors.BOLD}Method 2: Direct file read{Colors.RESET}")
token_path = os.path.expanduser("~/.huggingface/token")
print_info(f"Checking: {token_path}")
if os.path.exists(token_path):
    try:
        with open(token_path, 'r') as f:
            token = f.read().strip()
        if token:
            print_success(f"Token found in file (length: {len(token)} characters)")
        else:
            print_warning("File exists but is empty")
    except PermissionError:
        print_failure("Permission denied reading token file")
        print_info("Fix: Check file permissions with: ls -l ~/.huggingface/token")
    except Exception as e:
        print_failure(f"Error reading file: {e}")
else:
    print_warning("Token file does not exist")
    print_info("Fix: Run 'huggingface-cli login'")

# Method 3: HF_TOKEN environment variable
print(f"\n{Colors.BOLD}Method 3: HF_TOKEN environment variable{Colors.RESET}")
hf_token_env = os.environ.get("HF_TOKEN")
if hf_token_env:
    print_success(f"HF_TOKEN is set (length: {len(hf_token_env)} characters)")
else:
    print_warning("HF_TOKEN environment variable not set")
    print_info("Alternative: export HF_TOKEN=your_token_here")

# Method 4: HUGGINGFACE_TOKEN environment variable
print(f"\n{Colors.BOLD}Method 4: HUGGINGFACE_TOKEN environment variable{Colors.RESET}")
hf_token_alt_env = os.environ.get("HUGGINGFACE_TOKEN")
if hf_token_alt_env:
    print_success(f"HUGGINGFACE_TOKEN is set (length: {len(hf_token_alt_env)} characters)")
else:
    print_warning("HUGGINGFACE_TOKEN environment variable not set")
    print_info("Alternative: export HUGGINGFACE_TOKEN=your_token_here")

# Test 3: API Handler Import
print_header("Test 3: Import Application Modules")
try:
    from api_handler import HuggingFaceAPIHandler
    print_success("Successfully imported HuggingFaceAPIHandler")
except ImportError as e:
    print_failure(f"Failed to import api_handler: {e}")
    sys.exit(1)

# Test 4: Validate token if available
print_header("Test 4: Token Validation (if token available)")
final_token = None

# Try all methods to get a token
if hf_get_token and hf_get_token():
    final_token = hf_get_token()
    print_info("Using token from get_token()")
elif os.path.exists(token_path):
    try:
        with open(token_path, 'r') as f:
            final_token = f.read().strip()
        print_info("Using token from file")
    except:
        pass
elif hf_token_env:
    final_token = hf_token_env
    print_info("Using token from HF_TOKEN env var")
elif hf_token_alt_env:
    final_token = hf_token_alt_env
    print_info("Using token from HUGGINGFACE_TOKEN env var")

if final_token:
    print(f"\n{Colors.BOLD}Validating token with HuggingFace API...{Colors.RESET}")
    try:
        handler = HuggingFaceAPIHandler(final_token.strip())
        is_valid, message = handler.validate_key()

        if is_valid:
            print_success(f"Token validation successful: {message}")
        else:
            print_failure(f"Token validation failed: {message}")
    except Exception as e:
        print_failure(f"Error during validation: {e}")
else:
    print_warning("No token available for validation")
    print_info("To authenticate:")
    print_info("  1. Run: huggingface-cli login")
    print_info("  2. Or set: export HF_TOKEN=your_token_here")
    print_info("  3. Or use manual entry in the GUI")

# Test 5: Enhanced error messages
print_header("Test 5: Enhanced Error Messages")
print_info("Testing error message improvements...")

# Test with invalid token to see error message
if not final_token:
    print_info("Creating test handler with invalid token to check error messages")
    try:
        test_handler = HuggingFaceAPIHandler("invalid_token_for_testing")
        is_valid, message = test_handler.validate_key()
        print_info(f"Error message example: {message}")
        if "https://huggingface.co/settings/tokens" in message:
            print_success("Error messages include helpful links ✓")
        else:
            print_warning("Error messages could be more helpful")
    except Exception as e:
        print_warning(f"Could not test error messages: {e}")

# Summary
print_header("Test Summary")
print(f"\n{Colors.BOLD}Authentication Status:{Colors.RESET}")

if final_token:
    print_success("Token detected and available")
    print_info("The application should work correctly")
else:
    print_warning("No authentication token found")
    print_info("Follow the setup instructions above to authenticate")

print(f"\n{Colors.BOLD}Setup Instructions:{Colors.RESET}")
print_info("1. Install dependencies: pip install -r requirements.txt")
print_info("2. Authenticate: huggingface-cli login")
print_info("3. Run application: python main.py")
print_info("4. Use 'Debug Authentication' button in GUI for troubleshooting")

print(f"\n{Colors.BOLD}Log File Location:{Colors.RESET}")
log_file = os.path.expanduser("~/.llm_red_team_gui.log")
print_info(f"Detailed logs: {log_file}")

print_header("Test Complete")
print()
