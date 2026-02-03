"""
Debug script to test HuggingFace API key validation
Run this to see the exact error message
"""

import requests
import sys

def test_api_key(api_key: str):
    print("=" * 50)
    print("HuggingFace API Key Debug Test")
    print("=" * 50)

    # Check format
    print(f"\n1. API Key Format Check:")
    print(f"   Key starts with 'hf_': {api_key.startswith('hf_')}")
    print(f"   Key length: {len(api_key)}")

    # Test basic connectivity
    print(f"\n2. Testing basic connectivity to huggingface.co...")
    try:
        response = requests.get("https://huggingface.co", timeout=10)
        print(f"   Status: {response.status_code} (should be 200)")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test API endpoint without auth
    print(f"\n3. Testing API endpoint (no auth)...")
    try:
        response = requests.get("https://huggingface.co/api/whoami", timeout=10)
        print(f"   Status: {response.status_code} (401 expected without auth)")
        print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test with auth header
    print(f"\n4. Testing API endpoint WITH auth...")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(
            "https://huggingface.co/api/whoami",
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n   SUCCESS! User: {data.get('name', 'Unknown')}")
        elif response.status_code == 401:
            print(f"\n   FAILED: API returned 401 (Invalid/Expired API key)")
        else:
            print(f"\n   UNEXPECTED: Status {response.status_code}")

    except requests.exceptions.SSLError as e:
        print(f"   SSL ERROR: {e}")
        print("\n   This might be a certificate issue on Windows.")
        print("   Try: pip install --upgrade certifi")
    except requests.exceptions.ConnectionError as e:
        print(f"   CONNECTION ERROR: {e}")
    except requests.exceptions.Timeout:
        print(f"   TIMEOUT: Request took longer than 10 seconds")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test with session (like the actual code does)
    print(f"\n5. Testing with requests.Session (like the app does)...")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {api_key}"})
    try:
        response = session.get(
            "https://huggingface.co/api/whoami",
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    print("\n" + "=" * 50)
    print("Debug complete!")
    print("=" * 50)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = input("Enter your HuggingFace API key: ").strip()

    if not api_key:
        print("No API key provided!")
        sys.exit(1)

    test_api_key(api_key)
