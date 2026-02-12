# 🛡️ LLM Red Team GUI

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)
![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20%7C%20WSL2-lightgrey.svg)
![Built for Garak](https://img.shields.io/badge/Built%20for-Garak-red.svg)

A GTK desktop GUI for [Garak](https://github.com/NVIDIA/garak), the LLM vulnerability scanner. Instead of memorizing Garak CLI commands and probe names, this app lets you visually browse probes, configure scans, and read results through a guided step-by-step wizard.

---

## 📑 Table of Contents

- [🔍 What is Garak?](#-what-is-garak)
- [💻 Platform Support](#-platform-support)
- [✨ Features](#-features)
- [🖥️ Hardware Requirements](#️-hardware-requirements)
- [⚡ Quick Start](#-quick-start)
- [📦 Installation](#-installation)
- [⚙️ How It Works](#️-how-it-works)
- [🧪 Supported Probe Categories](#-supported-garak-probe-categories)
- [📖 Usage Guide](#-usage-guide)
- [🗂️ Project Structure](#️-project-structure)
- [⚖️ Responsible Use](#️-responsible-use)
- [📚 Resources](#-resources)
- [📄 License](#-license)

---

## 🔍 What is Garak?

[Garak](https://github.com/NVIDIA/garak) (Generative AI Red-teaming & Assessment Kit) is NVIDIA's open-source vulnerability scanner for large language models. It automatically probes LLMs for:

- 🔓 **Jailbreaks** — bypassing safety alignment (DAN, roleplay, hypothetical framing)
- 💉 **Prompt injection** — hijacking model behavior through crafted inputs
- 🔑 **Data leakage** — extracting training data or system prompts
- 🔤 **Encoding attacks** — obfuscation via Base64, ROT13, hex, Unicode
- ☣️ **Toxicity & bias** — generating harmful or biased content
- 🌀 **Hallucination** — producing false or fabricated information

Garak is normally run from the command line:

```bash
garak --model_type huggingface --model_name distilgpt2 --probes dan,encoding,promptinject
```

**This GUI eliminates the need to remember those commands.** You select probes from categorized checkboxes, pick a model, configure parameters, and click run. The app builds the Garak command, executes it, and parses the results into a readable format.

> [!TIP]
> 🆕 New to Garak? Check out the [Garak GitHub](https://github.com/NVIDIA/garak) and [Garak Docs](https://docs.garak.ai) to learn more about available probes and attack strategies.

---

## 💻 Platform Support

| Platform | Status |
|----------|--------|
| 🐧 Linux (native) | ✅ Fully supported |
| 🪟 WSL2 | ✅ Fully supported |
| 🍎 macOS | ⚠️ Not tested |
| 🪟 Windows (native) | ❌ Not supported |

> [!IMPORTANT]
> This application is designed for **Linux only**. Windows users should run it in WSL2 with Ubuntu 22.04.

---

## ✨ Features

- 🔎 **Visual probe browser** — select Garak probes from categorized checkboxes instead of memorizing probe names
- 🧙 **Guided setup wizard** — 7-step flow handles Garak detection, HuggingFace auth, model selection, probe picking, and configuration
- 📊 **Readable results** — pass/fail summary cards per probe with detailed failure inspection, parsed from Garak's JSONL report output
- 📡 **Live output streaming** — watch Garak stdout/stderr in real time with elapsed time and progress tracking
- 🤗 **HuggingFace integration** — test any model on HuggingFace Hub or a local endpoint
- 🎛️ **Configurable parameters** — set generations, temperature, and max tokens from the GUI
- 💾 **Hardware-aware** — warnings for 4GB VRAM limitations with verified model recommendations

---

## 🖥️ Hardware Requirements

Based on verified testing (GTX 1650, 4GB VRAM):

| Model | Status |
|-------|--------|
| distilgpt2 | ⭐ Recommended |
| gpt2 | ✅ Works |
| gpt2-medium | ✅ Works |
| TinyLlama-1.1B | ✅ Works |
| 7B+ models | ❌ Too large |

> [!WARNING]
> ⚠️ Models larger than ~1B parameters require more than 4GB VRAM. If you have limited GPU memory, stick with `distilgpt2` or `gpt2`.

---

## ⚡ Quick Start

Get up and running in 4 commands:

```bash
# 1️⃣ Clone and enter the repo
git clone <repo-url> && cd llm_security_gui

# 2️⃣ Install GTK system dependencies (Ubuntu/Debian)
sudo apt install -y python3-gi gir1.2-gtk-3.0

# 3️⃣ Create venv and install Python deps
python3 -m venv .venv --system-site-packages && source .venv/bin/activate && pip install -r requirements.txt

# 4️⃣ Launch the app
python app.py
```

> [!NOTE]
> 🔑 You'll also need Garak (`pip install garak`) and a HuggingFace API key ([get one here](https://huggingface.co/settings/tokens)). The app will guide you through setup on first launch.

---

## 📦 Installation

<details>
<summary><strong>📋 Full step-by-step installation guide</strong></summary>

### Prerequisites

- 🐧 **Linux** (native or WSL2)
- 🐍 Python 3.10+ (required for Garak)
- 🔬 Garak (`pip install garak`)
- 🔑 HuggingFace API key ([get one here](https://huggingface.co/settings/tokens))
- 🪟 WSL2 + Ubuntu 22.04 (recommended for Windows users)

### Steps

**1️⃣ Clone or download this repository:**

```bash
git clone <repo-url>
cd llm_security_gui
```

**2️⃣ Install system GTK dependencies (required for `gi` / GTK 3):**

Ubuntu / Debian:
```bash
sudo apt install -y python3-gi gir1.2-gtk-3.0
```

Arch Linux:
```bash
sudo pacman -Syu --needed python-gobject gtk3
```

**3️⃣ Create a virtual environment and install Python dependencies:**

```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

**4️⃣ Run the GTK preflight check:**

```bash
python scripts/check_gtk.py
```

**5️⃣ Verify Garak is installed:**

```bash
garak --version
```

**6️⃣ Set up HuggingFace authentication:**

```bash
hf auth login
hf auth whoami
# OR
export HF_TOKEN=your_token_here
```

> [!TIP]
> `huggingface-cli login` may still work as a legacy alias, but `hf auth login` is the current command.

**7️⃣ Run the application:**

```bash
python app.py
```

</details>

<details>
<summary><strong>🔧 GTK Troubleshooting</strong></summary>

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

---

**Step 1: 🖥️ Check display connectivity** from the same shell/venv you use to launch the app:

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

---

**Step 2: 📦 Ensure system GTK packages are installed:**

Ubuntu / Debian:
```bash
sudo apt install -y python3-gi gir1.2-gtk-3.0
```

Arch Linux:
```bash
sudo pacman -Syu --needed python-gobject gtk3
```

---

**Step 3: 🔄 Recreate `.venv` with system package visibility:**

```bash
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_gtk.py
```

---

**Step 4: 🏗️ If you must use an isolated venv** (no `--system-site-packages`), install native build deps first:

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

---

**Step 5: 🔗 Last resort** (advanced only) — symlink system `gi` into venv `site-packages`:

```bash
source .venv/bin/activate
VENV_SITE=$(python -c "import site; print(site.getsitepackages()[0])")
SYS_GI=$(python3 -c "import gi, pathlib; print(pathlib.Path(gi.__file__).resolve().parent)")
ln -s "$SYS_GI" "$VENV_SITE/gi"
```

> [!WARNING]
> ⚠️ Use this only if package installs are blocked. `--system-site-packages` is the preferred approach.

</details>

[⬆️ Back to top](#️-llm-red-team-gui)

---

## ⚙️ How It Works

This GUI is a frontend for Garak. It does not implement its own probes or payloads — all security testing runs through Garak's CLI.

```
  🧙 GUI Wizard                  🔬 Garak CLI                   📄 Output
 +-----------+    builds     +----------------+   produces   +------------------+
 | Select    | ------------> | python -m garak|  ---------> | .report.jsonl    |
 | probes,   |   command     | --model_type   |             | .hitlog.jsonl    |
 | model,    |               | --model_name   |             +------------------+
 | config    |               | --probes       |                     |
 +-----------+               +----------------+                     |
                                                          parses    |
 +-----------+                                                      |
 | Results   | <----------------------------------------------------+
 | pass/fail |   GarakReportParser reads JSONL
 | summaries |   and displays per-probe results
 +-----------+
```

**Execution flow:**
1. 🎯 You select probes and configure parameters in the GUI
2. ✅ The app validates inputs and builds a Garak CLI command
3. 🚀 Garak runs as a subprocess with live stdout/stderr streaming to the GUI
4. 📝 When complete, the app parses Garak's `.report.jsonl` and `.hitlog.jsonl` output files
5. 📊 Results are displayed as pass/fail summary cards with detailed attempt data

---

## 🧪 Supported Garak Probe Categories

The GUI organizes Garak's probes into these categories:

<details>
<summary><strong>🗂️ View all probe categories and CLI mappings</strong></summary>

| Garak Probe | What It Tests | Example CLI |
|-------------|---------------|-------------|
| `dan` | 🔓 "Do Anything Now" jailbreak variants that attempt to bypass safety alignment through persona manipulation | `garak --probes dan` |
| `encoding` | 🔤 Obfuscation attacks using Base64, ROT13, hex, reversed text, and Unicode to slip prompts past content filters | `garak --probes encoding` |
| `promptinject` | 💉 Direct prompt injection — instruction override, goal hijacking, delimiter escapes, system prompt extraction | `garak --probes promptinject` |
| `lmrc` | 📋 Language Model Risk Cards — tests for harmful content generation, bias, and other risks defined in research literature | `garak --probes lmrc` |
| `atkgen` | 🤖 Automated adversarial prompt generation using a red-team LLM to discover novel attack vectors | `garak --probes atkgen` |
| `gcg` | 🧬 Greedy Coordinate Gradient suffix attacks — research-grade optimization-based jailbreaks | `garak --probes gcg` |

The GUI also maps additional attack categories (multilingual bypasses, refusal bypass, RAG poisoning, goal hijacking, data extraction) to the appropriate Garak probes above.

Run `garak --list_probes` to see all available probes beyond what the GUI exposes.

</details>

<details>
<summary><strong>📟 Garak quick reference commands</strong></summary>

```bash
# 📋 List available probes, detectors, and generators
garak --list_probes
garak --list_detectors
garak --list_generators

# 🚀 Run a scan
garak --model_type huggingface --model_name distilgpt2 --probes dan,encoding

# 🔁 Run with multiple generations per probe
garak --model_type huggingface --model_name gpt2 --probes promptinject --generations 5

# 📄 Use a config file
garak --config your_config.yaml

# ℹ️ Check version
garak --version
```

</details>

[⬆️ Back to top](#️-llm-red-team-gui)

---

## 📖 Usage Guide

### Step 1: 🔧 Framework Setup
- The app checks Garak availability and version
- If Garak is missing, install it with `pip install garak` and click retry

### Step 2: 🔐 Authentication
- The app verifies HuggingFace CLI auth status
- Login with `hf auth login` if required, then retry

### Step 3: 🤖 Select Model
- Choose HuggingFace model ID or local endpoint mode
- `distilgpt2` is pre-filled as a lightweight default

### Step 4: 🧪 Choose Probes
- Browse Garak probes organized by attack category
- Select individual probes or use preset groups ("Recommended Set", "Advanced Threats")
- The GUI shows which Garak probe each selection maps to

### Step 5: ⚙️ Configure Run
- Set generations, temperature, and max tokens
- Review the Garak CLI commands that will be executed
- Choose output format and parallel mode as needed

### Step 6: 🚀 Run Test
- Start the assessment and watch live Garak output
- Track elapsed time and progress status
- Cancel at any time

### Step 7: 📊 Results
- View pass/fail summaries by probe and detector
- Inspect detailed failure attempts for each probe
- Export or save results

---

## 🗂️ Project Structure

<details>
<summary><strong>📁 View project file tree</strong></summary>

```
llm_security_gui/
├── 🚀 app.py               # Main GTK application entry point
├── 🧭 controller.py        # Wizard coordinator and navigation
├── ✅ check_controller.py  # Step 1-2 checks (Garak + HF auth)
├── ⚙️ workspace_controller.py # Step 3-5 setup/configuration
├── ▶️ run_controller.py    # Step 6 execution and live output
├── 📊 results_controller.py # Step 7 result presentation
├── 🌐 api_handler.py       # HuggingFace API interactions
├── 🧪 probes.py            # Garak probe categories and UI mappings
├── 🤗 hf_cli.py            # HuggingFace CLI detection/auth helpers
├── 🔬 garak_runner.py      # Garak subprocess execution wrapper
├── 📝 garak_report_parser.py # Structured parsing of Garak JSONL reports
├── 🛠️ scripts/check_gtk.py # GTK preflight validation
├── 📦 requirements.txt     # Dependencies (includes garak)
└── 📄 README.md           # This file
```

</details>

---

## ⚖️ Responsible Use

This tool is intended for:
- 🔬 Security researchers
- 🛡️ AI safety teams
- 🎯 Red team assessments
- 🏆 Bug bounty programs (HackerOne, Bugcrowd)

> [!CAUTION]
> 🚫 **Do NOT use for:**
> - Attacking production systems without permission
> - Creating actual harmful content
> - Any illegal activities
>
> ⚠️ Always obtain proper authorization before testing any system you do not own.

---

## 📚 Resources

- 🔬 [Garak GitHub](https://github.com/NVIDIA/garak) — LLM vulnerability scanner
- 📖 [Garak Documentation](https://docs.garak.ai) — probes, detectors, generators reference
- 🛡️ [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- 🤗 [HuggingFace NLP Course](https://huggingface.co/learn/nlp-course)
- 🏰 [Gandalf Challenge](https://gandalf.lakera.ai) — CTF for prompt injection

---

## 📄 License

MIT License - Use responsibly. 🤝
