# Implementation Plan (WSL/Linux Only)

## Summary
Implement the Linux/WSL-only build in `~/llm_security_gui/linux` using the isolated venv `~/llm_security_gui/llmSec`. Preserve a snapshot in `backup/`. Keep dependencies minimal and avoid `sudo`. Garak runs via `python -m garak` from the active venv.

## Goals
- Preserve current app in `backup/`
- Linux/WSL-only implementation
- Use isolated venv `llmSec`
- No `shell=True` in Garak runner
- No extra dependencies beyond the existing set
- Maintain the 6-step wizard flow

## Structure
- `~/llm_security_gui/backup/`
- `~/llm_security_gui/linux/`
- `~/llm_security_gui/PLAN.md`

## Dependency Policy
- `customtkinter>=5.2.2`
- `requests>=2.31.0`
- `huggingface_hub>=0.20.0`
- `PyYAML>=6.0`
- Optional: `aiohttp`, `Pillow` (only if already used)

## Environment
- Activate venv:
  - `source ~/llm_security_gui/llmSec/bin/activate`
- Install deps:
  - `pip install -r linux/requirements.txt`
- Run app:
  - `python linux/main.py`

## Garak Integration
- Always run via active venv:
  - `python -m garak ...`
- No `shell=True`
- Commands are built as argument lists

## Changes/Additions (Implemented)
- Created `~/llm_security_gui/backup/` from the Windows source.
- Created `~/llm_security_gui/linux/` from the Windows source.
- Replaced `linux/garak_runner.py` with a WSL-only, venv-based runner:
  - Uses `sys.executable -m garak`
  - Removed `shell=True` and Windows code paths
- Updated `linux/README.md` for WSL-only usage and `llmSec` venv instructions.
