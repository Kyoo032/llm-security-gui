"""Tests for garak_runner.py – command building, validation, execution."""

import unittest
from unittest.mock import MagicMock, patch

from garak_runner import GarakRunConfig, GarakRunResult, GarakRunner


class TestGarakRunConfig(unittest.TestCase):
    """Test GarakRunConfig immutability and defaults."""

    def test_default_values(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
        )
        self.assertEqual(config.generations, 1)
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.max_tokens, 512)
        self.assertFalse(config.verbose)
        self.assertTrue(config.parallel)
        self.assertEqual(config.output_dir, "./garak_reports/")

    def test_frozen(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
        )
        with self.assertRaises(AttributeError):
            config.model_name = "changed"


class TestGarakRunResult(unittest.TestCase):
    """Test GarakRunResult immutability."""

    def test_frozen(self):
        result = GarakRunResult(success=True, return_code=0)
        with self.assertRaises(AttributeError):
            result.success = False

    def test_default_values(self):
        result = GarakRunResult(success=False, return_code=1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertIsNone(result.report_path)
        self.assertIsNone(result.error)


class TestGarakRunnerCommandBuilding(unittest.TestCase):
    """Test command building and input validation."""

    def setUp(self):
        self.runner = GarakRunner()

    def test_basic_command(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
        )
        cmd = self.runner.build_command(config)
        self.assertEqual(cmd[:3], ["python", "-m", "garak"])
        self.assertIn("--model_type", cmd)
        self.assertIn("huggingface", cmd)
        self.assertIn("--model_name", cmd)
        self.assertIn("gpt2", cmd)
        self.assertIn("--probes", cmd)
        self.assertIn("dan", cmd)

    def test_multiple_probes(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan", "encoding", "promptinject"],
        )
        cmd = self.runner.build_command(config)
        probes_index = cmd.index("--probes")
        self.assertEqual(cmd[probes_index + 1], "dan,encoding,promptinject")

    def test_verbose_flag(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
            verbose=True,
        )
        cmd = self.runner.build_command(config)
        self.assertIn("-v", cmd)

    def test_generations_flag(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
            generations=5,
        )
        cmd = self.runner.build_command(config)
        gen_index = cmd.index("--generations")
        self.assertEqual(cmd[gen_index + 1], "5")

    def test_generations_default_not_in_cmd(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
            generations=1,
        )
        cmd = self.runner.build_command(config)
        self.assertNotIn("--generations", cmd)

    def test_invalid_model_name_chars(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2; rm -rf /",
            probes=["dan"],
        )
        with self.assertRaises(ValueError):
            self.runner.build_command(config)

    def test_invalid_model_name_empty(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="",
            probes=["dan"],
        )
        with self.assertRaises(ValueError):
            self.runner.build_command(config)

    def test_invalid_model_name_too_long(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="a" * 257,
            probes=["dan"],
        )
        with self.assertRaises(ValueError):
            self.runner.build_command(config)

    def test_invalid_probe_name_chars(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan; echo pwned"],
        )
        with self.assertRaises(ValueError):
            self.runner.build_command(config)

    def test_valid_model_with_slash(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            probes=["dan"],
        )
        cmd = self.runner.build_command(config)
        self.assertIn("TinyLlama/TinyLlama-1.1B-Chat-v1.0", cmd)

    def test_report_prefix(self):
        config = GarakRunConfig(
            model_type="huggingface",
            model_name="gpt2",
            probes=["dan"],
            report_prefix="my_test",
        )
        cmd = self.runner.build_command(config)
        prefix_index = cmd.index("--report_prefix")
        self.assertEqual(cmd[prefix_index + 1], "my_test")


class TestGarakRunnerFindCommand(unittest.TestCase):
    """Test garak command detection."""

    @patch("garak_runner.shutil.which")
    def test_garak_found(self, mock_which):
        mock_which.return_value = "/usr/local/bin/garak"
        self.assertEqual(GarakRunner.find_garak_command(), "garak")

    @patch("garak_runner.shutil.which")
    def test_garak_not_found(self, mock_which):
        mock_which.return_value = None
        self.assertIsNone(GarakRunner.find_garak_command())


class TestGarakRunnerCancel(unittest.TestCase):
    """Test run cancellation."""

    def test_cancel_sets_flag(self):
        runner = GarakRunner()
        runner.cancel()
        self.assertTrue(runner._cancel_requested)

    @patch("garak_runner.subprocess.Popen")
    def test_cancel_terminates_process(self, mock_popen):
        runner = GarakRunner()
        mock_proc = MagicMock()
        runner._process = mock_proc
        runner.cancel()
        mock_proc.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
