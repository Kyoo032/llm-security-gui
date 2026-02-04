# Security Best Practices Report

## Executive Summary
The review focused on local credential handling, results storage, export safety, and command execution. The primary risks were plaintext API key storage, permissive file permissions for sensitive results, CSV formula injection on export, and PATH-based command execution for Garak. All issues have been remediated in this change set.

## Scope
- `main.py`
- `results_manager.py`
- `garak_runner.py`
- `requirements.txt`

## Findings

### Medium

**SBP-001: API key storage should avoid plaintext files and require explicit user consent**
- **Impact**: A locally stored API key can be read by other local users/processes if file permissions are weak or backups are exposed.
- **Evidence**: `main.py:263` (load), `main.py:287` (save).
- **Remediation**: Prefer OS keychain via `keyring`, add explicit “Remember key” opt-in, and secure fallback file writes with `0600` permissions.

**SBP-002: Result files and exports should be written with restrictive permissions**
- **Impact**: Results include prompts and model outputs that can contain sensitive or harmful content, which should not be broadly readable on multi-user systems.
- **Evidence**: `results_manager.py:23`, `results_manager.py:39`, `results_manager.py:83`, `results_manager.py:98`.
- **Remediation**: Create results directory with `0700`, write files with `0600`, and use atomic writes.

**SBP-003: CSV export should prevent formula injection**
- **Impact**: Opening a CSV in spreadsheet software may execute attacker-controlled formulas (e.g., `=HYPERLINK(...)`).
- **Evidence**: `results_manager.py:34`, `results_manager.py:83`.
- **Remediation**: Sanitize CSV values that begin with `=`, `+`, `-`, or `@` by prefixing with `'`.

**SBP-004: Garak execution should use resolved absolute path**
- **Impact**: PATH hijacking could execute a malicious `garak` binary if present earlier in PATH.
- **Evidence**: `garak_runner.py:50`, `garak_runner.py:58`, `garak_runner.py:73`, `garak_runner.py:118`.
- **Remediation**: Resolve `garak` with `shutil.which` and run commands using that absolute path.

## Notes
- `requirements.txt` updated to include `keyring` for secure credential storage.
