#!/usr/bin/env python3
"""Unit tests for Hugging Face CLI helpers."""

from __future__ import annotations

import os
import sys
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hf_cli import check_hf_cli_auth, find_hf_cli_command


class TestHFCLIHelpers(unittest.TestCase):
    def test_find_hf_cli_prefers_hf(self):
        with patch("hf_cli.shutil.which") as which:
            which.side_effect = ["/usr/bin/hf", "/usr/bin/huggingface-cli"]
            self.assertEqual(find_hf_cli_command(), "hf")

    def test_find_hf_cli_legacy_fallback(self):
        with patch("hf_cli.shutil.which") as which:
            which.side_effect = [None, "/usr/bin/huggingface-cli"]
            self.assertEqual(find_hf_cli_command(), "huggingface-cli")

    def test_check_auth_not_installed(self):
        with patch("hf_cli.shutil.which", return_value=None):
            status = check_hf_cli_auth()
        self.assertFalse(status.installed)
        self.assertFalse(status.authenticated)
        self.assertIsNone(status.command)

    def test_check_auth_success_hf(self):
        with patch("hf_cli.shutil.which") as which, patch("hf_cli.subprocess.run") as run:
            which.side_effect = ["/usr/bin/hf", None]
            run.return_value = subprocess.CompletedProcess(
                args=["hf", "auth", "whoami"],
                returncode=0,
                stdout="username: alice\n",
                stderr="",
            )
            status = check_hf_cli_auth()
        self.assertTrue(status.installed)
        self.assertTrue(status.authenticated)
        self.assertEqual(status.command, "hf")
        self.assertEqual(status.username, "alice")

    def test_check_auth_fallback_subcommand(self):
        with patch("hf_cli.shutil.which") as which, patch("hf_cli.subprocess.run") as run:
            which.side_effect = ["/usr/bin/hf", None]
            run.side_effect = [
                subprocess.CompletedProcess(
                    args=["hf", "auth", "whoami"],
                    returncode=2,
                    stdout="",
                    stderr="unknown command",
                ),
                subprocess.CompletedProcess(
                    args=["hf", "whoami"],
                    returncode=0,
                    stdout="bob\n",
                    stderr="",
                ),
            ]
            status = check_hf_cli_auth()
        self.assertTrue(status.authenticated)
        self.assertEqual(status.username, "bob")

    def test_check_auth_timeout(self):
        with patch("hf_cli.shutil.which") as which, patch("hf_cli.subprocess.run") as run:
            which.side_effect = ["/usr/bin/hf", None]
            run.side_effect = subprocess.TimeoutExpired(cmd=["hf", "auth", "whoami"], timeout=8)
            status = check_hf_cli_auth()
        self.assertTrue(status.installed)
        self.assertFalse(status.authenticated)
        self.assertIn("timed out", status.detail)

    def test_check_auth_not_logged_in(self):
        with patch("hf_cli.shutil.which") as which, patch("hf_cli.subprocess.run") as run:
            which.side_effect = ["/usr/bin/hf", None]
            run.side_effect = [
                subprocess.CompletedProcess(
                    args=["hf", "auth", "whoami"],
                    returncode=1,
                    stdout="",
                    stderr="Not logged in",
                ),
                subprocess.CompletedProcess(
                    args=["hf", "whoami"],
                    returncode=1,
                    stdout="",
                    stderr="Not logged in",
                ),
            ]
            status = check_hf_cli_auth()
        self.assertTrue(status.installed)
        self.assertFalse(status.authenticated)
        self.assertIn("not logged in", status.detail.lower())

    def test_check_auth_network_error(self):
        with patch("hf_cli.shutil.which") as which, patch("hf_cli.subprocess.run") as run:
            which.side_effect = ["/usr/bin/hf", None]
            run.side_effect = [
                subprocess.CompletedProcess(
                    args=["hf", "auth", "whoami"],
                    returncode=1,
                    stdout="",
                    stderr="Failed to resolve 'huggingface.co'",
                ),
                subprocess.CompletedProcess(
                    args=["hf", "whoami"],
                    returncode=1,
                    stdout="",
                    stderr="MaxRetryError",
                ),
            ]
            status = check_hf_cli_auth()
        self.assertTrue(status.installed)
        self.assertFalse(status.authenticated)
        self.assertIn("could not reach huggingface.co", status.detail.lower())


if __name__ == "__main__":
    unittest.main()
