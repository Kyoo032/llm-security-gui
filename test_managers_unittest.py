#!/usr/bin/env python3
"""Unit tests for non-GUI probe management."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from probes import ProbeManager


class TestProbeManager(unittest.TestCase):
    def test_format_probe_prompt_includes_payload(self):
        manager = ProbeManager()
        prompt = manager.format_probe_prompt("dan_classic", "PAYLOAD_X")
        self.assertIsNotNone(prompt)
        self.assertIn("PAYLOAD_X", prompt)


if __name__ == "__main__":
    unittest.main()
