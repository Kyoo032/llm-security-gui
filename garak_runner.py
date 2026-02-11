"""Garak CLI command builder and subprocess executor."""

from __future__ import annotations

import logging
import re
import select
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

_SAFE_MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9_\-./: ]+$")
_SAFE_PROBE_PATTERN = re.compile(r"^[a-zA-Z0-9_. ]+$")


@dataclass(frozen=True)
class GarakRunConfig:
    """Immutable configuration for a Garak run."""

    model_type: str
    model_name: str
    probes: List[str]
    generations: int = 1
    temperature: float = 0.7
    max_tokens: int = 512
    verbose: bool = False
    parallel: bool = True
    report_prefix: str = ""
    output_dir: str = "./garak_reports/"


@dataclass(frozen=True)
class GarakRunResult:
    """Immutable result of a Garak run."""

    success: bool
    return_code: int
    report_path: Optional[str] = None
    hitlog_path: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


class GarakRunner:
    """Builds and executes Garak CLI commands with validation."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("garak_gui.runner")
        self._process: Optional[subprocess.Popen] = None
        self._cancel_requested = False
        self._lock = threading.Lock()

    @staticmethod
    def find_garak_command() -> Optional[str]:
        """Return the garak command if available."""
        if shutil.which("garak"):
            return "garak"
        return None

    def build_command(self, config: GarakRunConfig) -> List[str]:
        """Build a validated garak CLI command as argument list."""
        if not config.model_name or len(config.model_name) > 256:
            raise ValueError(f"Invalid model name length: {len(config.model_name)}")
        if not _SAFE_MODEL_PATTERN.match(config.model_name):
            raise ValueError(f"Invalid characters in model name: {config.model_name}")

        for probe in config.probes:
            if not probe or len(probe) > 128:
                raise ValueError(f"Invalid probe name length: {len(probe)}")
            if not _SAFE_PROBE_PATTERN.match(probe):
                raise ValueError(f"Invalid characters in probe name: {probe}")

        cmd = ["python", "-m", "garak"]

        cmd.extend(["--model_type", config.model_type])
        cmd.extend(["--model_name", config.model_name])

        if config.probes:
            probe_arg = ",".join(config.probes)
            cmd.extend(["--probes", probe_arg])

        if config.generations != 1:
            cmd.extend(["--generations", str(config.generations)])

        if config.report_prefix:
            cmd.extend(["--report_prefix", config.report_prefix])

        if config.verbose:
            cmd.append("-v")

        return cmd

    def run(
        self,
        config: GarakRunConfig,
        on_stdout_line: Callable[[str], None],
        on_stderr_line: Callable[[str], None],
        on_complete: Callable[[GarakRunResult], None],
    ) -> None:
        """Execute garak in a background thread, streaming output."""
        with self._lock:
            self._cancel_requested = False

        def _worker() -> None:
            stdout_lines: List[str] = []
            stderr_lines: List[str] = []
            report_path: Optional[str] = None
            hitlog_path: Optional[str] = None

            try:
                cmd = self.build_command(config)
                self.logger.info("Running garak: %s", " ".join(cmd))

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                with self._lock:
                    self._process = process

                # Read stdout and stderr line-by-line
                while True:
                    if self._cancel_requested:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        on_complete(
                            GarakRunResult(
                                success=False,
                                return_code=-1,
                                stdout="\n".join(stdout_lines),
                                stderr="\n".join(stderr_lines),
                                error="Canceled by user",
                            )
                        )
                        return

                    # Use select for non-blocking reads on Linux
                    readable = []
                    try:
                        readable, _, _ = select.select(
                            [process.stdout, process.stderr], [], [], 0.1
                        )
                    except (ValueError, OSError):
                        # Process pipes closed
                        break

                    for stream in readable:
                        line = stream.readline()
                        if not line:
                            continue
                        line = line.rstrip("\n")

                        if stream == process.stdout:
                            stdout_lines.append(line)
                            on_stdout_line(line)
                            # Check for report path in output
                            if ".report.jsonl" in line:
                                parts = line.split()
                                for part in parts:
                                    if ".report.jsonl" in part:
                                        report_path = part.strip()
                            if ".hitlog.jsonl" in line:
                                parts = line.split()
                                for part in parts:
                                    if ".hitlog.jsonl" in part:
                                        hitlog_path = part.strip()
                        else:
                            stderr_lines.append(line)
                            on_stderr_line(line)

                    if process.poll() is not None:
                        # Read remaining output
                        for line in (process.stdout.read() or "").splitlines():
                            stdout_lines.append(line)
                            on_stdout_line(line)
                        for line in (process.stderr.read() or "").splitlines():
                            stderr_lines.append(line)
                            on_stderr_line(line)
                        break

                return_code = process.returncode or 0

                with self._lock:
                    self._process = None

                on_complete(
                    GarakRunResult(
                        success=return_code == 0,
                        return_code=return_code,
                        report_path=report_path,
                        hitlog_path=hitlog_path,
                        stdout="\n".join(stdout_lines),
                        stderr="\n".join(stderr_lines),
                    )
                )

            except Exception as exc:
                self.logger.exception("Garak run failed")
                with self._lock:
                    self._process = None
                on_complete(
                    GarakRunResult(
                        success=False,
                        return_code=-1,
                        stdout="\n".join(stdout_lines),
                        stderr="\n".join(stderr_lines),
                        error=str(exc),
                    )
                )

        threading.Thread(target=_worker, daemon=True).start()

    def cancel(self) -> None:
        """Request cancellation of the current run."""
        with self._lock:
            self._cancel_requested = True
            if self._process is not None:
                try:
                    self._process.terminate()
                except OSError:
                    pass
