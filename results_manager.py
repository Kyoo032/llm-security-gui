"""
Results manager for saving/loading/exporting red team runs.

This module exists because older parts of the repo (and unit tests) import
`ResultsManager` from `results_manager.py`. The implementation is kept
dependency-free so it can be used without the GUI.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Validation pattern for path traversal prevention: require a simple *.json filename.
_SAFE_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+\.json$")


class ResultsManager:
    """Manages test results storage and simple export helpers."""

    def __init__(self, results_dir: str | None = None, max_results_files: int = 200):
        if results_dir is None:
            results_dir = os.path.expanduser("~/.llm_red_team_results")

        self.results_dir = results_dir
        self.max_results_files = max_results_files
        self.logger = logging.getLogger("llm_red_team_gui.results")
        self._ensure_private_dir()

    def _validate_filename(self, filename: str) -> bool:
        """Validate filename to prevent path traversal."""
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return False
        return bool(_SAFE_FILENAME_PATTERN.match(filename))

    def _ensure_private_dir(self) -> None:
        os.makedirs(self.results_dir, exist_ok=True)
        try:
            os.chmod(self.results_dir, 0o700)
        except Exception:
            # Best-effort on platforms/filesystems that don't support chmod.
            pass

    def _open_secure_write(self, filepath: str):
        fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        return os.fdopen(fd, "w", encoding="utf-8", newline="")

    def _sanitize_csv_value(self, value):
        # Prevent CSV/Excel formula injection.
        if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    def _enforce_rotation(self) -> None:
        if not self.max_results_files or self.max_results_files <= 0:
            return

        try:
            files = [f for f in os.listdir(self.results_dir) if f.endswith(".json")]
        except Exception:
            return

        files_with_mtime: list[tuple[str, float]] = []
        for name in files:
            path = os.path.join(self.results_dir, name)
            try:
                files_with_mtime.append((path, os.path.getmtime(path)))
            except Exception:
                continue

        files_with_mtime.sort(key=lambda x: x[1], reverse=True)
        for path, _mtime in files_with_mtime[self.max_results_files :]:
            try:
                os.remove(path)
            except Exception:
                pass

    def save_results(self, results: List[Dict], filename: str | None = None) -> str:
        """Save test results to a JSON file and return the path."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"red_team_results_{timestamp}.json"

        filepath = os.path.join(self.results_dir, filename)
        tmp_path = f"{filepath}.tmp"

        data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "successful_bypasses": sum(1 for r in results if r.get("success")),
            "results": results,
        }

        with self._open_secure_write(tmp_path) as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, filepath)
        try:
            os.chmod(filepath, 0o600)
        except Exception:
            pass

        self._enforce_rotation()
        return filepath

    def load_results(self, filename: str) -> Optional[Dict]:
        """Load results from file with path traversal protection."""
        if not self._validate_filename(filename):
            self.logger.warning("Invalid filename rejected: %s", filename)
            return None

        filepath = os.path.join(self.results_dir, filename)

        # Additional safety: verify resolved path is within results_dir.
        real_filepath = os.path.realpath(filepath)
        real_results_dir = os.path.realpath(self.results_dir)
        if not real_filepath.startswith(real_results_dir + os.sep):
            self.logger.warning("Path traversal attempt detected")
            return None

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_results(self) -> List[str]:
        """List all saved result files (newest first)."""
        try:
            files = [f for f in os.listdir(self.results_dir) if f.endswith(".json")]
        except Exception:
            return []
        return sorted(files, reverse=True)

    def export_csv(self, results: List[Dict], filepath: str) -> Tuple[bool, str]:
        """Export results to CSV (best-effort)."""
        if not results:
            return False, "No results to export"

        sanitized_results = [
            {k: self._sanitize_csv_value(v) for k, v in r.items()} for r in results
        ]

        try:
            with self._open_secure_write(filepath) as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(sanitized_results)
            return True, "Exported CSV"
        except Exception as e:
            return False, f"CSV export failed: {e}"

    def export_json(self, results: List[Dict], filepath: str) -> Tuple[bool, str]:
        """Export results to JSON (list-only export, not the full save_results envelope)."""
        if not results:
            return False, "No results to export"

        tmp_path = f"{filepath}.tmp"
        try:
            with self._open_secure_write(tmp_path) as f:
                json.dump(results, f, indent=2)
            os.replace(tmp_path, filepath)
            try:
                os.chmod(filepath, 0o600)
            except Exception:
                pass
            return True, "Exported JSON"
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False, f"JSON export failed: {e}"

    def generate_summary(self, results: List[Dict]) -> Dict:
        """Generate a lightweight summary of test results."""
        if not results:
            return {}

        total = len(results)
        successful = sum(1 for r in results if r.get("success"))

        by_probe: Dict[str, Dict[str, int]] = {}
        for r in results:
            probe = r.get("probe", "Unknown")
            by_probe.setdefault(probe, {"total": 0, "successful": 0})
            by_probe[probe]["total"] += 1
            if r.get("success"):
                by_probe[probe]["successful"] += 1

        by_payload: Dict[str, Dict[str, int]] = {}
        for r in results:
            payload = r.get("payload", "Unknown")
            by_payload.setdefault(payload, {"total": 0, "successful": 0})
            by_payload[payload]["total"] += 1
            if r.get("success"):
                by_payload[payload]["successful"] += 1

        return {
            "total_tests": total,
            "successful_bypasses": successful,
            "blocked": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "by_probe": by_probe,
            "by_payload": by_payload,
        }

