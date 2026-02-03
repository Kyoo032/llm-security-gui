# 🛡️ LLM Red Team GUI

A desktop application for security testing of Large Language Models using the HuggingFace Inference API, with Garak CLI integration.

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

- Python 3.10+ (required for Garak)
- HuggingFace API key ([get one here](https://huggingface.co/settings/tokens))
- WSL2 + Ubuntu 22.04 (recommended)

## 🔧 Installation

1. Clone or download this repository:
```bash
git clone <repo-url>
cd llm_red_team_gui
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Install Garak for CLI integration:
```bash
pip install garak
garak --version
```

4. Set up HuggingFace authentication:
```bash
huggingface-cli login
# OR
export HF_TOKEN=your_token_here
```

5. Run the application:
```bash
python main.py
```

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
- Key is saved locally for convenience

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
llm_red_team_gui/
├── main.py              # Main GUI application
├── api_handler.py       # HuggingFace API interactions
├── probes.py            # Security probes (Garak-aligned)
├── payloads.py          # Attack payloads
├── garak_runner.py      # Garak CLI integration
├── results_manager.py   # Results storage
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
