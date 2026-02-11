#!/usr/bin/env python3
"""Unit tests for non-GUI core managers."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from payloads import PayloadManager
from probes import ProbeManager
from results_manager import ResultsManager


class TestPayloadManager(unittest.TestCase):
    def test_catalog_payload_resolves_to_real_text(self):
        manager = PayloadManager()
        payload_text = manager.get_payload_text("harmful_malware")
        self.assertIn("keylogger", payload_text.lower())
        self.assertNotEqual(payload_text, "harmful_malware")

    def test_custom_payload_rejects_empty(self):
        manager = PayloadManager()
        ok, message = manager.add_custom_payload("   ")
        self.assertFalse(ok)
        self.assertIn("cannot be empty", message.lower())


class TestResultsManager(unittest.TestCase):
    def test_csv_formula_injection_is_sanitized(self):
        manager = ResultsManager(results_dir=tempfile.mkdtemp(prefix="rt_results_"))
        dangerous = "=2+2"
        sanitized = manager._sanitize_csv_value(dangerous)
        self.assertEqual(sanitized, "'=2+2")

    def test_load_results_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory(prefix="rt_results_") as tmpdir:
            manager = ResultsManager(results_dir=tmpdir)
            self.assertIsNone(manager.load_results("../etc/passwd"))


class TestProbeManager(unittest.TestCase):
    def test_format_probe_prompt_includes_payload(self):
        manager = ProbeManager()
        prompt = manager.format_probe_prompt("dan_classic", "PAYLOAD_X")
        self.assertIsNotNone(prompt)
        self.assertIn("PAYLOAD_X", prompt)


if __name__ == "__main__":
    unittest.main()
