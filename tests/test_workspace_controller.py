"""Tests for workspace_controller.py – probe presets and settings."""

import unittest

from workspace_controller import PROBE_PRESETS


class TestProbePresets(unittest.TestCase):
    """Test probe preset definitions."""

    def test_recommended_set_exists(self):
        self.assertIn("Recommended Set", PROBE_PRESETS)
        self.assertGreater(len(PROBE_PRESETS["Recommended Set"]), 0)

    def test_advanced_threats_exists(self):
        self.assertIn("Advanced Threats", PROBE_PRESETS)
        self.assertGreater(len(PROBE_PRESETS["Advanced Threats"]), 0)

    def test_presets_contain_strings(self):
        for name, categories in PROBE_PRESETS.items():
            for cat in categories:
                self.assertIsInstance(cat, str, f"Preset {name} has non-string: {cat}")

    def test_no_overlap_between_presets(self):
        rec = set(PROBE_PRESETS["Recommended Set"])
        adv = set(PROBE_PRESETS["Advanced Threats"])
        overlap = rec & adv
        self.assertEqual(len(overlap), 0, f"Overlap found: {overlap}")


class TestRunControllerProbeMapping(unittest.TestCase):
    """Test probe name mapping (category -> garak module)."""

    def test_mapping_known_categories(self):
        from run_controller import RunController

        mapped = RunController._map_probe_names(
            ["DAN Jailbreaks", "Encoding Attacks", "Prompt Injection"]
        )
        self.assertIn("dan", mapped)
        self.assertIn("encoding", mapped)
        self.assertIn("promptinject", mapped)

    def test_mapping_deduplicates(self):
        from run_controller import RunController

        # Refusal Bypass maps to "dan", same as DAN Jailbreaks
        mapped = RunController._map_probe_names(
            ["DAN Jailbreaks", "Refusal Bypass"]
        )
        self.assertEqual(mapped.count("dan"), 1)

    def test_mapping_empty(self):
        from run_controller import RunController

        mapped = RunController._map_probe_names([])
        self.assertEqual(len(mapped), 0)

    def test_mapping_unknown_category(self):
        from run_controller import RunController

        mapped = RunController._map_probe_names(["Unknown Category"])
        self.assertEqual(len(mapped), 1)
        # Should use lowercased, space-removed fallback
        self.assertEqual(mapped[0], "unknowncategory")


if __name__ == "__main__":
    unittest.main()
