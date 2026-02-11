"""
Prototype module wrapper.

Re-exports constants used by the GTK prototype from the repository-root
`compatibility.py` module.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from compatibility import *  # noqa: E402,F403

