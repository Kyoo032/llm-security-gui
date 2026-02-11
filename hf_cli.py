"""Helpers for Hugging Face CLI availability and auth checks."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Optional


@dataclass(frozen=True)
class HFCLIStatus:
    """Snapshot of local Hugging Face CLI authentication state."""

    command: Optional[str]
    installed: bool
    authenticated: bool
    username: str
    detail: str


def _extract_username(output: str) -> str:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("username:"):
            return line.split(":", 1)[1].strip() or "unknown"
        return line
    return "unknown"


def find_hf_cli_command() -> Optional[str]:
    """Return the preferred Hugging Face CLI command name if installed."""
    if shutil.which("hf"):
        return "hf"
    if shutil.which("huggingface-cli"):
        return "huggingface-cli"
    return None


def check_hf_cli_auth(timeout_seconds: int = 8) -> HFCLIStatus:
    """Check whether Hugging Face CLI is installed and authenticated."""
    command = find_hf_cli_command()
    if command is None:
        return HFCLIStatus(
            command=None,
            installed=False,
            authenticated=False,
            username="",
            detail="Hugging Face CLI is not installed",
        )

    if command == "hf":
        attempts = [["auth", "whoami"], ["whoami"]]
    else:
        attempts = [["whoami"], ["auth", "whoami"]]

    last_output = ""
    for index, args in enumerate(attempts):
        try:
            result = subprocess.run(
                [command, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return HFCLIStatus(
                command=command,
                installed=True,
                authenticated=False,
                username="",
                detail=f"{command} auth check timed out",
            )
        except OSError as exc:
            return HFCLIStatus(
                command=command,
                installed=False,
                authenticated=False,
                username="",
                detail=f"Failed to execute {command}: {exc}",
            )

        output = (result.stdout or "").strip()
        if result.returncode == 0:
            username = _extract_username(output)
            return HFCLIStatus(
                command=command,
                installed=True,
                authenticated=True,
                username=username,
                detail=f"Authenticated as {username}",
            )

        output_text = " ".join(
            part for part in ((result.stderr or "").strip(), output) if part
        ).strip()
        lowered_output = output_text.lower()
        is_cmd_form_error = (
            "invalid choice" in lowered_output
            or "unknown command" in lowered_output
            or "unrecognized arguments" in lowered_output
        )

        if is_cmd_form_error and index < len(attempts) - 1:
            if not last_output:
                last_output = output_text
            continue

        last_output = output_text
        break

    lowered = last_output.lower()
    if (
        "failed to resolve" in lowered
        or "name or service not known" in lowered
        or "connectionerror" in lowered
        or "maxretryerror" in lowered
        or "connection refused" in lowered
        or "temporary failure in name resolution" in lowered
    ):
        detail = f"{command} could not reach huggingface.co"
    elif "not logged in" in lowered or "login" in lowered:
        detail = f"{command} is installed but not logged in"
    elif last_output:
        detail = f"{command} auth check failed: {last_output}"
    else:
        detail = f"{command} auth check failed"

    return HFCLIStatus(
        command=command,
        installed=True,
        authenticated=False,
        username="",
        detail=detail,
    )
