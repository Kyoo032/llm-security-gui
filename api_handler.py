"""
HuggingFace API Handler
Handles all API interactions with HuggingFace using the official huggingface_hub library
"""

from typing import Dict, List, Tuple, Optional
import time
import os

from huggingface_hub import HfApi, InferenceClient
from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError


class HuggingFaceAPIHandler:
    """Handler for HuggingFace API interactions using official huggingface_hub library"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the API handler.

        Args:
            api_key: Optional HuggingFace API token. If not provided, will attempt to use cached token.
        """
        self.api_key = api_key
        self.hf_api = HfApi(token=api_key)
        self.inference_client = InferenceClient(token=api_key)

    @staticmethod
    def get_cached_token() -> Optional[str]:
        """
        Get the cached HuggingFace token from huggingface-cli login.

        Returns:
            The cached token if it exists, None otherwise.
        """
        # Check standard token location
        token_path = os.path.expanduser("~/.cache/huggingface/token")

        # Also check Windows-specific location
        if os.name == 'nt':
            alt_path = os.path.join(os.environ.get('USERPROFILE', ''), '.cache', 'huggingface', 'token')
            if os.path.exists(alt_path):
                token_path = alt_path

        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as f:
                    token = f.read().strip()
                    if token:
                        return token
            except Exception:
                pass

        return None

    @staticmethod
    def validate_cached_token() -> Tuple[bool, str, Optional[str]]:
        """
        Check if the cached token exists and is valid.

        Returns:
            Tuple of (is_valid, message, username)
        """
        token = HuggingFaceAPIHandler.get_cached_token()

        if not token:
            return False, "No cached token found", None

        try:
            api = HfApi(token=token)
            user_info = api.whoami()
            username = user_info.get('name', user_info.get('fullname', 'User'))
            return True, f"Token valid for user: {username}", username
        except HfHubHTTPError as e:
            if e.response.status_code == 401:
                return False, "Cached token is invalid or expired", None
            return False, f"API error: {e}", None
        except Exception as e:
            return False, f"Error validating token: {str(e)}", None

    def validate_key(self) -> Tuple[bool, str]:
        """Validate the API key by making a test request"""
        try:
            user_info = self.hf_api.whoami()
            username = user_info.get('name', user_info.get('fullname', 'User'))
            return True, f"Welcome, {username}!"
        except HfHubHTTPError as e:
            if e.response.status_code == 401:
                return False, "Invalid API key"
            return False, f"API error: {e.response.status_code}"
        except Exception as e:
            error_str = str(e).lower()
            if 'timeout' in error_str:
                return False, "Connection timeout"
            elif 'connection' in error_str:
                return False, "Connection error"
            return False, f"Error: {str(e)}"

    def search_models(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for models on HuggingFace Hub"""
        try:
            models = self.hf_api.list_models(
                search=query,
                filter="text-generation",
                sort="downloads",
                direction=-1,
                limit=limit
            )

            result = []
            for m in models:
                result.append({
                    'id': m.id,
                    'downloads': getattr(m, 'downloads', 0),
                    'likes': getattr(m, 'likes', 0),
                    'pipeline_tag': getattr(m, 'pipeline_tag', ''),
                    'tags': getattr(m, 'tags', [])
                })
            return result

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get detailed information about a model"""
        try:
            info = self.hf_api.model_info(model_id)
            return {
                'id': info.id,
                'downloads': getattr(info, 'downloads', 0),
                'likes': getattr(info, 'likes', 0),
                'pipeline_tag': getattr(info, 'pipeline_tag', ''),
                'tags': getattr(info, 'tags', []),
                'author': getattr(info, 'author', ''),
                'lastModified': getattr(info, 'lastModified', '')
            }
        except RepositoryNotFoundError:
            return None
        except Exception:
            return None

    def generate(
        self,
        prompt: str,
        model_id: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
        max_retries: int = 3
    ) -> Dict:
        """Generate text using the specified model"""

        for attempt in range(max_retries):
            try:
                # Use InferenceClient for text generation
                response = self.inference_client.text_generation(
                    prompt,
                    model=model_id,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    return_full_text=False
                )

                return {
                    'text': response,
                    'model': model_id,
                    'success': True
                }

            except HfHubHTTPError as e:
                if e.response.status_code == 503:
                    # Model is loading
                    time.sleep(min(20, 30))
                    continue
                elif e.response.status_code == 429:
                    # Rate limited
                    time.sleep(5 * (attempt + 1))
                    continue
                else:
                    return {
                        'error': f"API error: {e.response.status_code}",
                        'text': '',
                        'success': False
                    }

            except Exception as e:
                error_str = str(e).lower()
                if 'timeout' in error_str:
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    return {
                        'error': 'Request timeout',
                        'text': '',
                        'success': False
                    }

                # Check for model loading message
                if '503' in str(e) or 'loading' in error_str:
                    time.sleep(min(20, 30))
                    continue

                return {
                    'error': str(e),
                    'text': '',
                    'success': False
                }

        return {
            'error': 'Max retries exceeded',
            'text': '',
            'success': False
        }

    def test_model_availability(self, model_id: str) -> Tuple[bool, str]:
        """Test if a model is available and working"""
        try:
            result = self.generate(
                "Hello",
                model_id,
                max_tokens=10,
                max_retries=1
            )

            if result.get('success'):
                return True, "Model is available"
            else:
                return False, result.get('error', 'Unknown error')

        except Exception as e:
            return False, str(e)
