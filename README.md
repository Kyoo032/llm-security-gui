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
- **30+ attack payloads** - Covering various security categories
- **Hardware-aware** - Warnings for 4GB VRAM limitations
- **Custom payload support** - Add your own attack vectors
- **Export to JSON/CSV** - For further analysis

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

1. Ensure system GTK packages are installed:

Ubuntu / Debian:
```bash
sudo apt install -y python3-gi gir1.2-gtk-3.0
```

Arch Linux:
```bash
sudo pacman -Syu --needed python-gobject gtk3
```

2. Recreate `.venv` with system package visibility:
```bash
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_gtk.py
```

3. If you must use an isolated venv (no `--system-site-packages`), install native build deps first:

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

4. Last resort (advanced only): symlink system `gi` into venv `site-packages`:
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

### Step 1: API Key
- Enter your HuggingFace API key
- Key is saved only if you enable “Remember key”
- Stored in OS keychain when available; otherwise saved to `~/.llm_red_team_config.json` with restricted permissions

### Step 2: Select Model
- **Verified models** are highlighted (safe for 4GB VRAM)
- Warnings shown for 7B+ models
- Garak CLI commands auto-generated

### Step 3: Choose Probes
Select security probes (aligned with Garak):

| Category | Garak Probe |
|----------|-------------|
| **DAN Jailbreaks** | `dan` |
| **Encoding Attacks** | `encoding` |
| **Prompt Injection** | `promptinject` |
| **LMRC Risk Cards** | `lmrc` |
| **Attack Generation** | `atkgen` |
| **GCG Attacks** | `gcg` |
| **Multilingual** | `encoding` |
| **RAG Poisoning** | `promptinject` |

### Step 4: Select Payloads
Choose attack payloads or add custom ones.

### Step 5: Configure & Run
- Set generations per payload (1-10)
- Adjust max tokens (50-500)
- Review Garak CLI commands
- Start test

### Step 6: Results
- View success/failure rates
- Export to JSON or CSV

## 🏗️ Project Structure

```
llm_security_gui/
├── app.py               # Main GTK application entry point
├── controller.py        # GTK UI/controller workflow
├── api_handler.py       # HuggingFace API interactions
├── probes.py            # Security probes (Garak-aligned)
├── payloads.py          # Attack payloads
├── compatibility.py     # Probe/payload compatibility helpers
├── results_manager.py   # Results storage
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
