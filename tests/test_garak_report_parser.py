"""Tests for garak_report_parser.py – JSONL parsing and stdout parsing."""

import json
import os
import tempfile
import unittest

from garak_report_parser import (
    GarakAttempt,
    GarakProbeSummary,
    GarakReportParser,
    GarakSummary,
)


class TestGarakAttempt(unittest.TestCase):
    """Test GarakAttempt dataclass."""

    def test_frozen(self):
        attempt = GarakAttempt(
            probe="dan",
            detector="always.Pass",
            status="evaluated",
            prompt="test",
            output="response",
            passed=True,
            score=1.0,
        )
        with self.assertRaises(AttributeError):
            attempt.passed = False


class TestGarakSummary(unittest.TestCase):
    """Test GarakSummary dataclass."""

    def test_empty_summary(self):
        summary = GarakSummary(
            total_attempts=0,
            total_passed=0,
            total_failed=0,
            pass_rate=0.0,
            probes_run=0,
        )
        self.assertEqual(summary.total_attempts, 0)
        self.assertEqual(len(summary.by_probe), 0)


class TestGarakReportParserJsonl(unittest.TestCase):
    """Test JSONL report parsing."""

    def setUp(self):
        self.parser = GarakReportParser()

    def test_parse_empty_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            f.write("")
            path = f.name
        try:
            summary = self.parser.parse_report(path)
            self.assertEqual(summary.total_attempts, 0)
            self.assertEqual(summary.probes_run, 0)
        finally:
            os.unlink(path)

    def test_parse_nonexistent_file(self):
        summary = self.parser.parse_report("/nonexistent/path.jsonl")
        self.assertEqual(summary.total_attempts, 0)

    def test_parse_single_pass(self):
        entries = [
            {
                "probe": "dan.Dan_11_0",
                "detector": "always.Pass",
                "passed": True,
                "prompt": "test prompt",
                "output": "safe response",
                "status": "evaluated",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
            path = f.name
        try:
            summary = self.parser.parse_report(path)
            self.assertEqual(summary.total_attempts, 1)
            self.assertEqual(summary.total_passed, 1)
            self.assertEqual(summary.total_failed, 0)
            self.assertAlmostEqual(summary.pass_rate, 1.0)
            self.assertEqual(summary.probes_run, 1)
        finally:
            os.unlink(path)

    def test_parse_mixed_results(self):
        entries = [
            {
                "probe": "dan.Dan_11_0",
                "detector": "mitigation.MitigationBypass",
                "passed": True,
                "prompt": "p1",
                "output": "r1",
            },
            {
                "probe": "dan.Dan_11_0",
                "detector": "mitigation.MitigationBypass",
                "passed": True,
                "prompt": "p2",
                "output": "r2",
            },
            {
                "probe": "dan.Dan_11_0",
                "detector": "mitigation.MitigationBypass",
                "passed": False,
                "prompt": "p3",
                "output": "r3",
            },
            {
                "probe": "encoding.Base64",
                "detector": "encoding.DecodeMatch",
                "passed": True,
                "prompt": "p4",
                "output": "r4",
            },
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
            path = f.name
        try:
            summary = self.parser.parse_report(path)
            self.assertEqual(summary.total_attempts, 4)
            self.assertEqual(summary.total_passed, 3)
            self.assertEqual(summary.total_failed, 1)
            self.assertAlmostEqual(summary.pass_rate, 0.75)
            self.assertEqual(summary.probes_run, 2)

            # Check per-probe breakdown
            dan_summary = next(
                s for s in summary.by_probe if "dan" in s.probe
            )
            self.assertEqual(dan_summary.passed, 2)
            self.assertEqual(dan_summary.failed, 1)
        finally:
            os.unlink(path)

    def test_parse_malformed_line(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            f.write('{"probe":"dan","detector":"x","passed":true}\n')
            f.write("this is not json\n")
            f.write('{"probe":"dan","detector":"x","passed":false}\n')
            path = f.name
        try:
            summary = self.parser.parse_report(path)
            self.assertEqual(summary.total_attempts, 2)
            self.assertEqual(summary.total_passed, 1)
            self.assertEqual(summary.total_failed, 1)
        finally:
            os.unlink(path)


class TestGarakReportParserHitlog(unittest.TestCase):
    """Test hitlog parsing."""

    def setUp(self):
        self.parser = GarakReportParser()

    def test_parse_hitlog(self):
        entries = [
            {
                "probe": "dan.Dan_11_0",
                "detector": "always.Fail",
                "prompt": "jailbreak attempt",
                "output": "unsafe response",
                "passed": False,
                "status": "evaluated",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
            path = f.name
        try:
            attempts = self.parser.parse_hitlog(path)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].probe, "dan.Dan_11_0")
            self.assertFalse(attempts[0].passed)
        finally:
            os.unlink(path)

    def test_parse_hitlog_nonexistent(self):
        attempts = self.parser.parse_hitlog("/nonexistent/hitlog.jsonl")
        self.assertEqual(len(attempts), 0)


class TestGarakReportParserStdout(unittest.TestCase):
    """Test stdout parsing (fallback when JSONL unavailable)."""

    def setUp(self):
        self.parser = GarakReportParser()

    def test_parse_stdout_pass_fail(self):
        stdout = """garak LLM vulnerability scanner v0.9
probes: promptinject
  promptinject.HijackHalfPrompt: PASS (100.0%)
  promptinject.HijackFull: PASS (100.0%)
probes: dan
  dan.Dan_11_0: FAIL (75.0% - 3/4 probes failed)
  dan.DeveloperMode: PASS (100.0%)
"""
        summary = self.parser.parse_stdout(stdout)
        self.assertEqual(summary.total_passed, 3)
        self.assertEqual(summary.total_failed, 1)
        self.assertEqual(summary.probes_run, 4)
        self.assertAlmostEqual(summary.pass_rate, 0.75)

    def test_parse_stdout_empty(self):
        summary = self.parser.parse_stdout("")
        self.assertEqual(summary.total_attempts, 0)
        self.assertEqual(summary.probes_run, 0)

    def test_parse_stdout_no_results(self):
        stdout = "garak LLM vulnerability scanner v0.9\nLoading model...\n"
        summary = self.parser.parse_stdout(stdout)
        self.assertEqual(summary.total_attempts, 0)

    def test_parse_stdout_all_pass(self):
        stdout = "  encoding.Base64: PASS (100.0%)\n"
        summary = self.parser.parse_stdout(stdout)
        self.assertEqual(summary.total_passed, 1)
        self.assertEqual(summary.total_failed, 0)
        self.assertAlmostEqual(summary.pass_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
