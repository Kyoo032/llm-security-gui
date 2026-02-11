#!/usr/bin/env python3
"""Unit tests for the GTK prototype payload catalog (no GTK imports)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPrototypePayloadCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parent
        cls.proto_dir = repo_root / "prototype" / "gtk_shell"
        cls.payloads_mod = _load_module(
            "proto_payloads",
            cls.proto_dir / "payloads.py",
        )
        cls.compat_mod = _load_module(
            "proto_compatibility",
            cls.proto_dir / "compatibility.py",
        )

    def test_payload_count_is_large(self):
        manager = self.payloads_mod.PayloadManager()
        self.assertGreaterEqual(
            len(manager.payloads),
            127,  # 27 baseline + 100 expansion target
        )

    def test_payloads_have_required_fields(self):
        manager = self.payloads_mod.PayloadManager()
        required = {"id", "name", "category", "text", "severity"}
        for payload_id, payload in manager.payloads.items():
            with self.subTest(payload_id=payload_id):
                self.assertTrue(required.issubset(payload.keys()))
                self.assertEqual(payload.get("id"), payload_id)
                self.assertIsInstance(payload.get("text"), str)

    def test_categories_match_compatibility_enum(self):
        manager = self.payloads_mod.PayloadManager()
        categories = {p["category"] for p in manager.payloads.values()}
        all_categories = set(self.compat_mod.ALL_PAYLOAD_CATEGORIES)
        missing = sorted(categories - all_categories)
        self.assertEqual(missing, [])

    def test_get_categories_is_display_only(self):
        manager = self.payloads_mod.PayloadManager()
        grouped = manager.get_categories()
        for cat, items in grouped.items():
            self.assertIsInstance(cat, str)
            for item in items:
                # The tree list should not include source metadata.
                self.assertEqual(set(item.keys()), {"id", "name", "severity"})

    def test_payload_text_does_not_include_provenance(self):
        manager = self.payloads_mod.PayloadManager()
        # Pick a payload with metadata.
        payload = manager.get_payload("system_prompt_extract")
        self.assertIn("source", payload)
        text = manager.get_payload_text("system_prompt_extract")
        self.assertEqual(text, payload["text"])
        # Ensure we didn't accidentally concatenate URLs into the prompt text.
        self.assertNotIn("http", text.lower())


if __name__ == "__main__":
    unittest.main()

