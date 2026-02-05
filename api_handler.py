"""
HuggingFace API Handler
Handles all API interactions with HuggingFace Inference API
"""

import requests
from typing import Dict, List, Tuple, Optional
import time
import logging


class HuggingFaceAPIHandler:
    """Handler for HuggingFace API interactions"""
    
    BASE_URL = "https://api-inference.huggingface.co/models"
    HUB_API = "https://huggingface.co/api"
    DEFAULT_TIMEOUTS = {
        "validate": 10,
        "search": 15,
        "model_info": 10,
        "generate": 60,
    }
    
    def __init__(self, api_key: str, timeouts: Optional[Dict[str, int]] = None):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.timeouts = dict(self.DEFAULT_TIMEOUTS)
        if timeouts:
            self.timeouts.update(timeouts)
        self._rate_limited_until = 0.0
        self.logger = logging.getLogger("llm_red_team_gui.api")
    
    def validate_key(self) -> Tuple[bool, str]:
        """Validate the API key by making a test request"""
        try:
            # Log what we're sending (for debugging)
            self.logger.info("=" * 60)
            self.logger.info("Validating HuggingFace token...")
            self.logger.info(f"Token length: {len(self.api_key)}")
            self.logger.info(f"Token starts with 'hf_': {self.api_key.startswith('hf_')}")
            self.logger.info(f"Token prefix (first 10 chars): {self.api_key[:10] if len(self.api_key) >= 10 else self.api_key}")
            self.logger.info(f"Authorization header: Bearer {self.api_key[:10]}...")

            # Try to get user info (using v2 API for modern tokens)
            response = self.session.get(
                "https://huggingface.co/api/whoami-v2",
                timeout=self.timeouts["validate"]
            )

            # Log the response details
            self.logger.info(f"Response status code: {response.status_code}")
            self.logger.info(f"Response headers: {dict(response.headers)}")
            self.logger.info(f"Response body: {response.text[:500]}")  # First 500 chars
            self.logger.info("=" * 60)

            if response.status_code == 200:
                data = response.json()
                username = data.get('name', 'User')
                self.logger.info(f"✓ Validation successful for user: {username}")
                return True, f"Welcome, {username}!"
            elif response.status_code == 401:
                # Include response body in error message for debugging
                error_detail = response.text[:200] if response.text else "No error details"
                self.logger.error(f"401 Unauthorized. API response: {error_detail}")
                return False, f"Invalid or expired token. API response: {error_detail}"
            elif response.status_code == 403:
                error_detail = response.text[:200] if response.text else "No error details"
                self.logger.error(f"403 Forbidden. API response: {error_detail}")
                return False, f"Token lacks required permissions. API response: {error_detail}"
            elif response.status_code == 429:
                return False, "Rate limited. Try again in a few moments"
            else:
                error_detail = response.text[:200] if response.text else "No error details"
                return False, f"API error {response.status_code}: {error_detail}"

        except requests.exceptions.Timeout:
            self.logger.error("Network timeout during validation")
            return False, "Network timeout. Check your internet connection"
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            return False, "Cannot reach HuggingFace servers. Check your internet connection"
        except Exception as e:
            self.logger.exception("validate_key failed")
            return False, f"Error: {str(e)}"
    
    def search_models(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for models on HuggingFace Hub"""
        try:
            if time.time() < self._rate_limited_until:
                return []

            params = {
                'search': query,
                'filter': 'text-generation',
                'sort': 'downloads',
                'direction': '-1',
                'limit': limit
            }
            
            response = self.session.get(
                f"{self.HUB_API}/models",
                params=params,
                timeout=self.timeouts["search"]
            )
            
            if response.status_code == 200:
                try:
                    models = response.json()
                except ValueError:
                    self.logger.warning("search_models returned non-JSON response")
                    return []
                return [
                    {
                        'id': m.get('modelId', m.get('id', '')),
                        'downloads': m.get('downloads', 0),
                        'likes': m.get('likes', 0),
                        'pipeline_tag': m.get('pipeline_tag', ''),
                        'tags': m.get('tags', [])
                    }
                    for m in models if isinstance(m, dict)
                ]
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 10
                self._rate_limited_until = time.time() + wait_time
            return []
            
        except Exception as e:
            self.logger.exception("Search error: %s", e)
            return []
    
    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get detailed information about a model"""
        try:
            response = self.session.get(
                f"{self.HUB_API}/models/{model_id}",
                timeout=self.timeouts["model_info"]
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception:
            self.logger.exception("get_model_info failed")
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
        if time.time() < self._rate_limited_until:
            wait = max(0, int(self._rate_limited_until - time.time()))
            return {
                'error': f'Rate limited. Retry in {wait}s',
                'text': '',
                'success': False,
                'rate_limited': True,
                'retry_after': wait
            }

        url = f"{self.BASE_URL}/{model_id}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": True,
                "return_full_text": False
            },
            "options": {
                "wait_for_model": True
            }
        }
        
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.timeouts["generate"]
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                    except ValueError:
                        return {
                            'error': 'Invalid JSON response',
                            'text': response.text,
                            'success': False
                        }
                    
                    # Handle different response formats
                    if isinstance(result, list) and len(result) > 0:
                        first = result[0]
                        if isinstance(first, dict):
                            text = first.get('generated_text', '')
                        else:
                            text = str(first)
                    elif isinstance(result, dict):
                        text = result.get('generated_text', '')
                    else:
                        text = str(result)
                    
                    return {
                        'text': text,
                        'model': model_id,
                        'success': True
                    }
                
                elif response.status_code == 503:
                    # Model is loading
                    try:
                        data = response.json()
                    except ValueError:
                        data = {}
                    wait_time = data.get('estimated_time', 20)
                    time.sleep(min(wait_time, 30))
                    continue
                
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = response.headers.get("Retry-After")
                    wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
                    self._rate_limited_until = time.time() + wait_time
                    time.sleep(wait_time)
                    continue
                
                else:
                    return {
                        'error': f"API error: {response.status_code}",
                        'text': '',
                        'success': False
                    }
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return {
                    'error': 'Request timeout',
                    'text': '',
                    'success': False
                }
                
            except Exception as e:
                self.logger.exception("generate failed")
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
