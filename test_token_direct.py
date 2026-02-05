#!/usr/bin/env python3
"""
Standalone HuggingFace Token Test Script
Tests a HuggingFace token directly without the GUI.
"""
import requests
import sys

def test_token(token):
    """Test a HuggingFace token by calling the whoami API endpoint"""
    print("=" * 70)
    print("HuggingFace Token Direct Test")
    print("=" * 70)

    # Token analysis
    print(f"\n[Token Info]")
    print(f"  Length: {len(token)}")
    print(f"  Starts with 'hf_': {token.startswith('hf_')}")
    print(f"  First 15 chars: {token[:15]}...")
    print(f"  Last 5 chars: ...{token[-5:]}")

    # Check for non-ASCII characters
    is_ascii = token.isascii()
    print(f"  Is ASCII: {is_ascii}")
    if not is_ascii:
        print("  ⚠️ WARNING: Token contains non-ASCII characters!")

    # Check for control characters
    has_control_chars = any(ord(c) < 32 for c in token)
    print(f"  Has control chars: {has_control_chars}")
    if has_control_chars:
        print("  ⚠️ WARNING: Token contains hidden control characters!")

    # API call
    print(f"\n[API Request]")
    print(f"  URL: https://huggingface.co/api/whoami-v2")
    print(f"  Method: GET")
    print(f"  Authorization: Bearer {token[:15]}...")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        print(f"\n[Sending Request...]")
        response = requests.get(
            "https://huggingface.co/api/whoami-v2",
            headers=headers,
            timeout=10
        )

        print(f"\n[API Response]")
        print(f"  Status Code: {response.status_code}")
        print(f"  Status Text: {response.reason}")
        print(f"\n[Response Headers]")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")

        print(f"\n[Response Body]")
        print(f"  {response.text}")

        print(f"\n{'=' * 70}")
        if response.status_code == 200:
            try:
                data = response.json()
                username = data.get('name', 'Unknown')
                print(f"✅ SUCCESS: Token is valid!")
                print(f"   Authenticated as: {username}")
                print(f"   Token type: {data.get('type', 'Unknown')}")
                if 'orgs' in data:
                    print(f"   Organizations: {len(data.get('orgs', []))}")
                return True
            except Exception as e:
                print(f"✅ SUCCESS: Status 200, but JSON parse failed: {e}")
                return True
        elif response.status_code == 401:
            print(f"❌ FAILED: Token is invalid or expired")
            print(f"   Generate a new token at: https://huggingface.co/settings/tokens")
            return False
        elif response.status_code == 403:
            print(f"❌ FAILED: Token lacks required permissions")
            print(f"   Ensure 'read' scope is enabled at: https://huggingface.co/settings/tokens")
            return False
        else:
            print(f"❌ FAILED: Unexpected status code {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(f"\n❌ ERROR: Request timed out")
        print(f"   Check your internet connection")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: Connection failed")
        print(f"   {e}")
        print(f"   Check your internet connection")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error")
        print(f"   {type(e).__name__}: {e}")
        return False
    finally:
        print("=" * 70)

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_token_direct.py YOUR_TOKEN")
        print("\nExample:")
        print("  python test_token_direct.py hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        print("\nYou can also pipe the token:")
        print("  echo 'hf_xxxx...' | python test_token_direct.py -")
        sys.exit(1)

    token = sys.argv[1].strip()

    # Allow reading from stdin
    if token == '-':
        print("Reading token from stdin...")
        token = input().strip()

    if not token:
        print("Error: Token is empty")
        sys.exit(1)

    success = test_token(token)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
