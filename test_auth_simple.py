#!/usr/bin/env python3
"""
Simple authentication test without Unicode characters (Windows-compatible)
"""

import os
import sys

print("\n" + "=" * 70)
print("HuggingFace Authentication Test Suite".center(70))
print("=" * 70 + "\n")

# Test 1: Import huggingface_hub
print("=" * 70)
print("Test 1: Import huggingface_hub".center(70))
print("=" * 70 + "\n")

try:
    from huggingface_hub import get_token as hf_get_token
    print("[OK] Successfully imported huggingface_hub.get_token")
    import huggingface_hub
    print(f"[INFO] Version: {huggingface_hub.__version__}")
except ImportError as e:
    print(f"[FAIL] Failed to import huggingface_hub: {e}")
    print("[FIX] Run: pip install -U 'huggingface_hub[cli]'")
    sys.exit(1)

# Test 2: Check token detection methods
print("\n" + "=" * 70)
print("Test 2: Token Detection Methods".center(70))
print("=" * 70 + "\n")

token_found = False

# Method 1: get_token()
print("Method 1: huggingface_hub.get_token()")
try:
    token = hf_get_token()
    if token:
        print(f"[OK] Token found (length: {len(token)} characters)")
        print(f"[INFO] Starts with: {token[:10]}...")
        token_found = True
    else:
        print("[WARN] No token found via get_token()")
        print("[INFO] This is expected if not logged in")
except Exception as e:
    print(f"[FAIL] Error calling get_token(): {e}")

# Method 2: Direct file reading
print("\nMethod 2: Direct file read")
token_path = os.path.expanduser("~/.huggingface/token")
print(f"[INFO] Checking: {token_path}")
if os.path.exists(token_path):
    try:
        with open(token_path, 'r') as f:
            token = f.read().strip()
        if token:
            print(f"[OK] Token found in file (length: {len(token)} characters)")
            if not token_found:
                token_found = True
        else:
            print("[WARN] File exists but is empty")
    except PermissionError:
        print("[FAIL] Permission denied reading token file")
        print("[FIX] Check file permissions: ls -l ~/.huggingface/token")
    except Exception as e:
        print(f"[FAIL] Error reading file: {e}")
else:
    print("[WARN] Token file does not exist")
    print("[FIX] Run: huggingface-cli login")

# Method 3: HF_TOKEN environment variable
print("\nMethod 3: HF_TOKEN environment variable")
hf_token_env = os.environ.get("HF_TOKEN")
if hf_token_env:
    print(f"[OK] HF_TOKEN is set (length: {len(hf_token_env)} characters)")
    if not token_found:
        token_found = True
else:
    print("[WARN] HF_TOKEN environment variable not set")
    print("[INFO] Alternative: export HF_TOKEN=your_token_here")

# Method 4: HUGGINGFACE_TOKEN environment variable
print("\nMethod 4: HUGGINGFACE_TOKEN environment variable")
hf_token_alt_env = os.environ.get("HUGGINGFACE_TOKEN")
if hf_token_alt_env:
    print(f"[OK] HUGGINGFACE_TOKEN is set (length: {len(hf_token_alt_env)} characters)")
    if not token_found:
        token_found = True
else:
    print("[WARN] HUGGINGFACE_TOKEN environment variable not set")
    print("[INFO] Alternative: export HUGGINGFACE_TOKEN=your_token_here")

# Test 3: API Handler Import
print("\n" + "=" * 70)
print("Test 3: Import Application Modules".center(70))
print("=" * 70 + "\n")

try:
    from api_handler import HuggingFaceAPIHandler
    print("[OK] Successfully imported HuggingFaceAPIHandler")
except ImportError as e:
    print(f"[FAIL] Failed to import api_handler: {e}")
    sys.exit(1)

# Test 4: Validate token if available
print("\n" + "=" * 70)
print("Test 4: Token Validation (if token available)".center(70))
print("=" * 70 + "\n")

final_token = None

# Try all methods to get a token
if hf_get_token and hf_get_token():
    final_token = hf_get_token()
    print("[INFO] Using token from get_token()")
elif os.path.exists(token_path):
    try:
        with open(token_path, 'r') as f:
            final_token = f.read().strip()
        print("[INFO] Using token from file")
    except:
        pass
elif hf_token_env:
    final_token = hf_token_env
    print("[INFO] Using token from HF_TOKEN env var")
elif hf_token_alt_env:
    final_token = hf_token_alt_env
    print("[INFO] Using token from HUGGINGFACE_TOKEN env var")

if final_token:
    print("\nValidating token with HuggingFace API...")
    try:
        handler = HuggingFaceAPIHandler(final_token.strip())
        is_valid, message = handler.validate_key()

        if is_valid:
            print(f"[OK] Token validation successful: {message}")
        else:
            print(f"[FAIL] Token validation failed: {message}")
    except Exception as e:
        print(f"[FAIL] Error during validation: {e}")
else:
    print("[WARN] No token available for validation")
    print("[INFO] To authenticate:")
    print("[INFO]   1. Run: huggingface-cli login")
    print("[INFO]   2. Or set: export HF_TOKEN=your_token_here")
    print("[INFO]   3. Or use manual entry in the GUI")

# Summary
print("\n" + "=" * 70)
print("Test Summary".center(70))
print("=" * 70 + "\n")

print("Authentication Status:")
if token_found:
    print("[OK] Token detected via at least one method")
    print("[INFO] The application should work correctly")
else:
    print("[WARN] No authentication token found")
    print("[INFO] Follow the setup instructions below to authenticate")

print("\nSetup Instructions:")
print("[1] Install dependencies: pip install -r requirements.txt")
print("[2] Authenticate: huggingface-cli login")
print("[3] Run application: python main.py")
print("[4] Use 'Debug Authentication' button in GUI for troubleshooting")

print("\nLog File Location:")
log_file = os.path.expanduser("~/.llm_red_team_gui.log")
print(f"[INFO] Detailed logs: {log_file}")

print("\n" + "=" * 70)
print("Test Complete".center(70))
print("=" * 70 + "\n")
