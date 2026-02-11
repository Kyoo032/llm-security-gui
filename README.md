# 🛡️ LLM Red Team GUI

A desktop application for security testing of Large Language Models using the HuggingFace Inference API, with Garak CLI integration.

## 🐧 Platform Support

| Platform | Status |
|----------|--------|
| Linux (native) | ✅ Fully supported |
| WSL2 | ✅ Fully supported |
| macOS | ⚠️ Not tested |
| Windows (native) | ❌ Not supported |

**This application is designed for Linux only.** Windows users should run it in WSL2.

## 🚀 Features

- **Step-by-step wizard interface** - Easy to follow workflow
- **HuggingFace API integration** - Test any model on HuggingFace Hub
- **Garak CLI compatibility** - Probes aligned with Garak categories
- **20+ built-in security probes** - DAN, encoding, promptinject, lmrc, atkgen, gcg
- **Hardware-aware** - Warnings for 4GB VRAM limitations
- **Live run monitoring** - Stream Garak output with progress updates
- **Results summaries** - Per-probe pass/fail cards and run details

## ⚠️ Hardware Requirements

Based on verified testing (GTX 1650, 4GB VRAM):

| Model | Status |
|-------|--------|
| distilgpt2 | ✅ Recommended |
| gpt2 | ✅ Works |
| gpt2-medium | ✅ Works |
| TinyLlama-1.1B | ✅ Works |
| 7B+ models | ❌ Too large |

## 📋 Requirements

- **Linux** (native or WSL2)
- Python 3.10+ (required for Garak)
- HuggingFace API key ([get one here](https://huggingface.co/settings/tokens))
- WSL2 + Ubuntu 22.04 (recommended for Windows users)

## 🔧 Installation

1. Clone or download this repository:
```bash
git clone <repo-url>
cd llm_security_gui
```

2. Install system GTK dependencies (required for `gi` / GTK 3):

Ubuntu / Debian:
```bash
sudo apt install -y python3-gi gir1.2-gtk-3.0
```

Arch Linux:
```bash
sudo pacman -Syu --needed python-gobject gtk3
```

3. Create a virtual environment and install Python dependencies:
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run the GTK preflight check:
```bash
python scripts/check_gtk.py
```

5. (Optional) Install Garak for CLI integration:
```bash
pip install garak
garak --version
```

6. Set up HuggingFace authentication:
```bash
hf auth login
hf auth whoami
# OR
export HF_TOKEN=your_token_here
```

`huggingface-cli login` may still work as a legacy alias, but `hf auth login` is the current command.

7. Run the application:
```bash
python app.py
```

### GTK Troubleshooting

If you see either of these errors:

```text
ModuleNotFoundError: No module named 'gi'
```

```text
Preparing metadata (pyproject.toml) did not run successfully
...
ERROR: Dependency 'girepository-2.0' is required but not found
```

```text
GTK could not connect to a display server.
DISPLAY=:0, WAYLAND_DISPLAY=wayland-0
```

1. Check display connectivity from the same shell/venv you use to launch the app:
```bash
python - <<'PY'
import os, gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk
r = Gtk.init_check(None)
ok = bool(r[0]) if isinstance(r, tuple) else bool(r)
print("DISPLAY", os.environ.get("DISPLAY"))
print("WAYLAND_DISPLAY", os.environ.get("WAYLAND_DISPLAY"))
print("XDG_RUNTIME_DIR", os.environ.get("XDG_RUNTIME_DIR"))
print("gtk_init_ok", ok)
print("gdk_default_display", Gdk.Display.get_default())
PY
```
If `gtk_init_ok` is `False` or `gdk_default_display` is `None`, restart WSLg from
Windows PowerShell with `wsl --shutdown`, then open a fresh Ubuntu shell and retry.

2. Ensure system GTK packages are installed:

Ubuntu / Debian:
```bash
sudo apt install -y python3-gi gir1.2-gtk-3.0
```

Arch Linux:
```bash
sudo pacman -Syu --needed python-gobject gtk3
```

3. Recreate `.venv` with system package visibility:
```bash
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_gtk.py
```

4. If you must use an isolated venv (no `--system-site-packages`), install native build deps first:

Ubuntu / Debian:
```bash
sudo apt install -y build-essential pkg-config cmake gobject-introspection libgirepository-2.0-dev libcairo2-dev python3-dev
```

Arch Linux:
```bash
sudo pacman -Syu --needed base-devel pkgconf cmake gobject-introspection cairo python
```

Then create isolated venv and install:
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_gtk.py
```

5. Last resort (advanced only): symlink system `gi` into venv `site-packages`:
```bash
source .venv/bin/activate
VENV_SITE=$(python -c "import site; print(site.getsitepackages()[0])")
SYS_GI=$(python3 -c "import gi, pathlib; print(pathlib.Path(gi.__file__).resolve().parent)")
ln -s "$SYS_GI" "$VENV_SITE/gi"
```
Use this only if package installs are blocked; `--system-site-packages` is preferred.

## 🔬 Garak Integration

This app's probes are aligned with Garak categories for compatibility:

| Garak Probe | Description | CLI Command |
|-------------|-------------|-------------|
| `encoding` | Encoding-based bypasses | `garak --model_type huggingface --model_name gpt2 --probes encoding` |
| `dan` | "Do Anything Now" jailbreaks | `garak --model_type huggingface --model_name distilgpt2 --probes dan` |
| `promptinject` | Direct prompt injection | `garak --model_type huggingface --model_name distilgpt2 --probes promptinject.HijackHateHumansMini` |
| `lmrc` | Language Model Risk Cards | `garak --model_type huggingface --model_name gpt2 --probes lmrc` |
| `atkgen` | Attack generation | `garak --model_type huggingface --model_name gpt2 --probes atkgen` |
| `gcg` | Greedy Coordinate Gradient | `garak --model_type huggingface --model_name gpt2 --probes gcg` |

### Garak Quick Reference
```bash
garak --list_probes
garak --list_detectors
garak --list_generators
garak --version
garak --config your_config.yaml
```

## 📖 Usage Guide

### Step 1: Framework Setup
- The app checks Garak availability and version
- If Garak is missing, install it and click retry

### Step 2: Authentication
- The app verifies HuggingFace CLI auth status
- Login with `hf auth login` if required, then retry

### Step 3: Select Model
- Choose HuggingFace model ID or local endpoint mode
- `distilgpt2` is pre-filled as a lightweight default

### Step 4: Choose Probes
Select security probes (aligned with Garak):

| Category | Garak Probe |
|----------|-------------|
| **DAN Jailbreaks** | `dan` |
| **Encoding Attacks** | `encoding` |
| **Prompt Injection** | `promptinject` |
| **LMRC Risk Cards** | `lmrc` |
| **Attack Generation** | `atkgen` |
| **GCG Attacks** | `gcg` |
| **Multilingual Attacks** | `encoding` |
| **RAG Poisoning** | `promptinject` |
| **Refusal Bypass** | `dan` |
| **Goal Hijacking** | `promptinject` |
| **Data Extraction** | `promptinject` |

### Step 5: Configure Run
- Set generations, temperature, and max tokens
- Review Garak CLI commands
- Choose output format and parallel mode as needed

### Step 6: Run Test
- Start the assessment and watch live stdout/stderr output
- Track elapsed time and progress status

### Step 7: Results
- View pass/fail summaries by probe and detector
- Inspect detailed failure attempts for each probe

## 🏗️ Project Structure

```
llm_security_gui/
├── app.py               # Main GTK application entry point
├── controller.py        # Wizard coordinator and navigation
├── check_controller.py  # Step 1-2 checks (Garak + HF auth)
├── workspace_controller.py # Step 3-5 setup/configuration
├── run_controller.py    # Step 6 execution and live output
├── results_controller.py # Step 7 result presentation
├── api_handler.py       # HuggingFace API interactions
├── probes.py            # Security probes (Garak-aligned)
├── hf_cli.py            # HuggingFace CLI detection/auth helpers
├── garak_runner.py      # Garak subprocess execution wrapper
├── garak_report_parser.py # Structured parsing of Garak reports
├── scripts/check_gtk.py # GTK preflight validation
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## 🔬 Attack Vectors (from Garak Reference)

- **Prompt Injection** — direct manipulation via user input
- **Jailbreaking** — bypassing safety guardrails (DAN, encoding, multilingual)
- **System Prompt Extraction** — leaking system instructions
- **Data Extraction** — exfiltrating training/context data
- **Refusal Bypass** — circumventing content filters
- **Goal Hijacking** — redirecting model behavior
- **RAG Poisoning** — injecting malicious content into vector stores

## 🛡️ Defense Mechanisms (Know to Beat)

- **Guardrails AI** — input/output validation
- **NeMo Guardrails** — NVIDIA's dialog safety
- **Rebuff** — prompt injection detection
- **LLM Guard** — comprehensive protection

Key defenses: input/output filters, semantic similarity checks, canary tokens.

## ⚠️ Responsible Use

This tool is intended for:
- Security researchers
- AI safety teams
- Red team assessments
- Bug bounty programs (HackerOne, Bugcrowd)

**Do NOT use for:**
- Attacking production systems without permission
- Creating actual harmful content
- Any illegal activities

## 📚 Resources

- [Garak Docs](https://github.com/leondz/garak)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [HuggingFace NLP Course](https://huggingface.co/learn/nlp-course)
- [Gandalf Challenge](https://gandalf.lakera.ai) — CTF for prompt injection

## 📄 License

MIT License - Use responsibly.
