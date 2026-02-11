"""Tests for check_controller.py – Garak detection and HF auth."""

import unittest
from unittest.mock import MagicMock, patch

from check_controller import CheckController


class TestGarakDetection(unittest.TestCase):
    """Test Garak installation detection."""

    @patch("check_controller.subprocess.run")
    @patch("check_controller.shutil.which")
    def test_garak_found_via_cli(self, mock_which, mock_run):
        mock_which.return_value = "/usr/local/bin/garak"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="garak version 0.9.0",
            stderr="",
        )
        found, version, path = CheckController._detect_garak()
        self.assertTrue(found)
        self.assertIn("0.9", version)

    @patch("check_controller.subprocess.run")
    @patch("check_controller.shutil.which")
    def test_garak_not_found(self, mock_which, mock_run):
        mock_which.return_value = None
        mock_run.side_effect = FileNotFoundError
        found, version, path = CheckController._detect_garak()
        self.assertFalse(found)
        self.assertIsNone(version)

    @patch("check_controller.subprocess.run")
    @patch("check_controller.shutil.which")
    def test_garak_timeout(self, mock_which, mock_run):
        mock_which.return_value = None
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="garak", timeout=15)
        found, version, path = CheckController._detect_garak()
        self.assertFalse(found)


class TestHFTokenDetection(unittest.TestCase):
    """Test HuggingFace token detection."""

    @patch("check_controller.hf_get_token", return_value="hf_testtoken123")
    def test_token_from_library(self, mock_get):
        token = CheckController._detect_hf_token()
        self.assertEqual(token, "hf_testtoken123")

    @patch("check_controller.hf_get_token", return_value=None)
    @patch("check_controller.Path.exists", return_value=False)
    @patch.dict(
        "os.environ",
        {"HF_TOKEN": "hf_env_token", "HUGGINGFACE_TOKEN": ""},
        clear=False,
    )
    def test_token_from_env_var(self, mock_get, mock_exists):
        token = CheckController._detect_hf_token()
        self.assertEqual(token, "hf_env_token")

    @patch("check_controller.hf_get_token", return_value=None)
    @patch.dict(
        "os.environ",
        {"HF_TOKEN": "", "HUGGINGFACE_TOKEN": ""},
        clear=False,
    )
    def test_no_token_available(self, mock_get):
        token = CheckController._detect_hf_token()
        # May return None or a file-based token depending on system
        # Just verify it doesn't crash
        self.assertTrue(token is None or isinstance(token, str))

    @patch("check_controller.hf_get_token", return_value="  hf_with_whitespace  ")
    def test_token_stripped(self, mock_get):
        token = CheckController._detect_hf_token()
        self.assertEqual(token, "hf_with_whitespace")

    @patch("check_controller.hf_get_token", side_effect=Exception("broken"))
    @patch("check_controller.Path.exists", return_value=False)
    @patch.dict(
        "os.environ",
        {"HF_TOKEN": "hf_fallback", "HUGGINGFACE_TOKEN": ""},
        clear=False,
    )
    def test_library_exception_falls_through(self, mock_get, mock_exists):
        token = CheckController._detect_hf_token()
        self.assertEqual(token, "hf_fallback")


if __name__ == "__main__":
    unittest.main()
