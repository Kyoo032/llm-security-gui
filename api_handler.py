"""
HuggingFace API handler.

This file is kept as a stable import target for existing scripts/docs
(`from api_handler import HuggingFaceAPIHandler`).
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

import requests


class HuggingFaceAPIHandler:
    """Handler for HuggingFace Hub + Inference API interactions."""

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
        self.session.verify = True
        self.logger = logging.getLogger("llm_red_team_gui.api")

    def validate_key(self) -> Tuple[bool, str]:
        """Validate the API key by calling the whoami endpoint."""
        try:
            self.logger.info("Validating HuggingFace token...")

            response = self.session.get(
                "https://huggingface.co/api/whoami-v2",
                timeout=self.timeouts["validate"],
            )

            if response.status_code == 200:
                data = response.json()
                username = data.get("name", "User")
                self.logger.info("Validation successful for user: %s", username)
                return True, f"Welcome, {username}!"
            if response.status_code == 401:
                self.logger.error("401 Unauthorized during token validation")
                return (
                    False,
                    "Invalid or expired token. Check token at https://huggingface.co/settings/tokens",
                )
            if response.status_code == 403:
                self.logger.error("403 Forbidden during token validation")
                return False, "Token lacks required permissions. Ensure read access is enabled"
            if response.status_code == 429:
                return False, "Rate limited. Try again in a few moments"
            return False, f"API error {response.status_code}"
        except requests.exceptions.Timeout:
            self.logger.error("Network timeout during validation")
            return False, "Network timeout. Check your internet connection"
        except requests.exceptions.ConnectionError as e:
            self.logger.error("Connection error: %s", e)
            return False, "Cannot reach HuggingFace servers. Check your internet connection"
        except (ValueError, KeyError, TypeError) as e:
            self.logger.exception("validate_key failed")
            return False, f"Error: {str(e)}"

    def search_models(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for text-generation models on the Hub."""
        try:
            if time.time() < self._rate_limited_until:
                return []

            params = {
                "search": query,
                "filter": "text-generation",
                "sort": "downloads",
                "direction": "-1",
                "limit": limit,
            }

            response = self.session.get(
                f"{self.HUB_API}/models",
                params=params,
                timeout=self.timeouts["search"],
            )

            if response.status_code == 200:
                try:
                    models = response.json()
                except ValueError:
                    self.logger.warning("search_models returned non-JSON response")
                    return []
                return [
                    {
                        "id": m.get("modelId", m.get("id", "")),
                        "downloads": m.get("downloads", 0),
                        "likes": m.get("likes", 0),
                        "pipeline_tag": m.get("pipeline_tag", ""),
                        "tags": m.get("tags", []),
                    }
                    for m in models
                    if isinstance(m, dict)
                ]

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 10
                self._rate_limited_until = time.time() + wait_time
            return []
        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            self.logger.debug("search_models failed: %s", e)
            return []

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get detailed model metadata."""
        try:
            response = self.session.get(
                f"{self.HUB_API}/models/{model_id}",
                timeout=self.timeouts["model_info"],
            )
            if response.status_code == 200:
                return response.json()
            return None
        except (requests.exceptions.RequestException, ValueError) as exc:
            self.logger.debug("get_model_info failed: %s", exc)
            return None

    def generate(
        self,
        prompt: str,
        model_id: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> Dict:
        """Generate text via the HF Inference API."""
        if time.time() < self._rate_limited_until:
            wait = max(0, int(self._rate_limited_until - time.time()))
            return {
                "error": f"Rate limited. Retry in {wait}s",
                "text": "",
                "success": False,
                "rate_limited": True,
                "retry_after": wait,
            }

        url = f"{self.BASE_URL}/{model_id}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": True,
                "return_full_text": False,
            },
            "options": {"wait_for_model": True},
        }

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.timeouts["generate"],
                )

                if response.status_code == 200:
                    try:
                        result = response.json()
                    except ValueError:
                        return {
                            "error": "Invalid JSON response",
                            "text": response.text,
                            "success": False,
                        }

                    if isinstance(result, list) and result:
                        first = result[0]
                        text = first.get("generated_text", "") if isinstance(first, dict) else str(first)
                    elif isinstance(result, dict):
                        text = result.get("generated_text", "")
                    else:
                        text = str(result)

                    return {"text": text, "model": model_id, "success": True}

                if response.status_code == 503:
                    try:
                        data = response.json()
                    except ValueError:
                        data = {}
                    wait_time = data.get("estimated_time", 20)
                    time.sleep(min(wait_time, 30))
                    continue

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
                    self._rate_limited_until = time.time() + wait_time
                    time.sleep(wait_time)
                    continue

                return {
                    "error": f"API error: {response.status_code}",
                    "text": "",
                    "success": False,
                }
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return {"error": "Request timeout", "text": "", "success": False}
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                self.logger.debug("generate failed: %s", e)
                return {"error": str(e), "text": "", "success": False}

        return {"error": "Max retries exceeded", "text": "", "success": False}

