"""Parser for Garak JSONL report and hitlog files."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class GarakAttempt:
    """A single test attempt from a Garak run."""

    probe: str
    detector: str
    status: str
    prompt: str
    output: str
    passed: Optional[bool]
    score: Optional[float]


@dataclass(frozen=True)
class GarakProbeSummary:
    """Summary of results for one probe+detector combination."""

    probe: str
    detector: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    attempts: List[GarakAttempt] = field(default_factory=list)


@dataclass(frozen=True)
class GarakSummary:
    """Overall summary of a Garak run."""

    total_attempts: int
    total_passed: int
    total_failed: int
    pass_rate: float
    probes_run: int
    by_probe: List[GarakProbeSummary] = field(default_factory=list)


class GarakReportParser:
    """Parses Garak report.jsonl and hitlog.jsonl files."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("garak_gui.report_parser")

    def parse_report(self, report_path: str) -> GarakSummary:
        """Parse a .report.jsonl file into a structured summary."""
        path = Path(report_path)
        if not path.exists():
            self.logger.warning("Report file not found: %s", report_path)
            return GarakSummary(
                total_attempts=0,
                total_passed=0,
                total_failed=0,
                pass_rate=0.0,
                probes_run=0,
            )

        entries = self._read_jsonl(path)
        return self._aggregate(entries)

    def parse_hitlog(self, hitlog_path: str) -> List[GarakAttempt]:
        """Parse a .hitlog.jsonl file for vulnerability-only entries."""
        path = Path(hitlog_path)
        if not path.exists():
            self.logger.warning("Hitlog file not found: %s", hitlog_path)
            return []

        entries = self._read_jsonl(path)
        return [self._entry_to_attempt(e) for e in entries]

    def parse_stdout(self, stdout: str) -> GarakSummary:
        """Parse Garak stdout output for a basic summary when JSONL unavailable."""
        probe_results: Dict[str, Dict[str, int]] = {}
        total_passed = 0
        total_failed = 0

        for line in stdout.splitlines():
            line = line.strip()
            # Lines like: "  probe.name: PASS (100.0%)"
            # or "  probe.name: FAIL (75.0% - 3/4 probes failed)"
            if ": PASS" in line or ": FAIL" in line:
                parts = line.split(":", 1)
                if len(parts) < 2:
                    continue
                probe_name = parts[0].strip()
                result_part = parts[1].strip()
                is_pass = result_part.startswith("PASS")

                if probe_name not in probe_results:
                    probe_results[probe_name] = {"passed": 0, "failed": 0}

                if is_pass:
                    probe_results[probe_name]["passed"] += 1
                    total_passed += 1
                else:
                    probe_results[probe_name]["failed"] += 1
                    total_failed += 1

        by_probe = []
        for probe_name, counts in probe_results.items():
            total = counts["passed"] + counts["failed"]
            rate = counts["passed"] / total if total > 0 else 0.0
            by_probe.append(
                GarakProbeSummary(
                    probe=probe_name,
                    detector="(from stdout)",
                    total=total,
                    passed=counts["passed"],
                    failed=counts["failed"],
                    pass_rate=rate,
                )
            )

        total = total_passed + total_failed
        return GarakSummary(
            total_attempts=total,
            total_passed=total_passed,
            total_failed=total_failed,
            pass_rate=total_passed / total if total > 0 else 0.0,
            probes_run=len(probe_results),
            by_probe=by_probe,
        )

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        """Read a JSONL file, returning a list of dicts."""
        entries: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line_num, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        self.logger.warning(
                            "Skipping malformed JSON at %s:%d", path, line_num
                        )
        except OSError as exc:
            self.logger.error("Failed to read %s: %s", path, exc)
        return entries

    def _entry_to_attempt(self, entry: Dict[str, Any]) -> GarakAttempt:
        """Convert a JSONL entry dict to a GarakAttempt."""
        return GarakAttempt(
            probe=str(entry.get("probe", "")),
            detector=str(entry.get("detector", "")),
            status=str(entry.get("status", "")),
            prompt=str(entry.get("prompt", "")),
            output=str(entry.get("output", entry.get("response", ""))),
            passed=entry.get("passed"),
            score=entry.get("score"),
        )

    def _aggregate(self, entries: List[Dict[str, Any]]) -> GarakSummary:
        """Aggregate JSONL entries into a summary."""
        combo_map: Dict[str, Dict[str, Any]] = {}

        for entry in entries:
            probe = str(entry.get("probe", "unknown"))
            detector = str(entry.get("detector", "unknown"))
            key = f"{probe}|{detector}"

            if key not in combo_map:
                combo_map[key] = {
                    "probe": probe,
                    "detector": detector,
                    "passed": 0,
                    "failed": 0,
                    "attempts": [],
                }

            attempt = self._entry_to_attempt(entry)
            combo_map[key]["attempts"].append(attempt)

            passed = entry.get("passed")
            if passed is True:
                combo_map[key]["passed"] += 1
            elif passed is False:
                combo_map[key]["failed"] += 1

        by_probe = []
        total_passed = 0
        total_failed = 0

        for data in combo_map.values():
            p = data["passed"]
            f = data["failed"]
            total = p + f
            total_passed += p
            total_failed += f
            by_probe.append(
                GarakProbeSummary(
                    probe=data["probe"],
                    detector=data["detector"],
                    total=total,
                    passed=p,
                    failed=f,
                    pass_rate=p / total if total > 0 else 0.0,
                    attempts=data["attempts"],
                )
            )

        grand_total = total_passed + total_failed
        return GarakSummary(
            total_attempts=grand_total,
            total_passed=total_passed,
            total_failed=total_failed,
            pass_rate=total_passed / grand_total if grand_total > 0 else 0.0,
            probes_run=len(combo_map),
            by_probe=by_probe,
        )
