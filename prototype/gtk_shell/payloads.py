"""
Prototype module wrapper.

Some tests load modules from `prototype/gtk_shell/*.py` paths. The repo's
canonical implementations live at the repository root (e.g. `payloads.py`),
so this file re-exports the current `PayloadManager`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from payloads import PayloadManager  # noqa: E402,F401

