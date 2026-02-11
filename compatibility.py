"""
Probe-Payload Compatibility Matrix and Model Weight Configuration.

Maps probe categories to compatible payload categories, and defines
model weight tiers for workload warnings.

Edit the values here when you have researched exact mappings --
the controller reads these dicts at startup.
"""

from __future__ import annotations

# All payload categories (must match payloads.py 'category' values)
ALL_PAYLOAD_CATEGORIES: frozenset[str] = frozenset([
    "Harmful Content",
    "Privacy Violation",
    "Illegal Activities",
    "Misinformation",
    "Hate Speech",
    "System Exploitation",
    "Encoded Payloads",
    "Context Manipulation",
    "Indirect Injection",
    "Manipulation",
    "Benign (Baseline)",
])

# Probe category -> compatible payload categories
PROBE_PAYLOAD_COMPATIBILITY: dict[str, frozenset[str]] = {
    "DAN Jailbreaks": ALL_PAYLOAD_CATEGORIES,

    "Encoding Attacks": frozenset([
        "Harmful Content",
        "System Exploitation",
        "Encoded Payloads",
        "Privacy Violation",
    ]),

    "Prompt Injection": ALL_PAYLOAD_CATEGORIES,

    "LMRC Risk Cards": frozenset([
        "Harmful Content",
        "Misinformation",
        "Hate Speech",
        "Privacy Violation",
        "Illegal Activities",
    ]),

    "Attack Generation": ALL_PAYLOAD_CATEGORIES,

    "GCG Attacks": frozenset([
        "Harmful Content",
        "System Exploitation",
        "Illegal Activities",
    ]),

    "Multilingual Attacks": ALL_PAYLOAD_CATEGORIES,

    "Refusal Bypass": frozenset([
        "Harmful Content",
        "Illegal Activities",
        "Privacy Violation",
        "Hate Speech",
        "Misinformation",
    ]),

    "Goal Hijacking": frozenset([
        "System Exploitation",
        "Manipulation",
        "Context Manipulation",
        "Harmful Content",
    ]),

    "RAG Poisoning": frozenset([
        "System Exploitation",
        "Indirect Injection",
        "Context Manipulation",
        "Misinformation",
        "Manipulation",
    ]),

    "Data Extraction": frozenset([
        "System Exploitation",
        "Privacy Violation",
    ]),
}

# Payload categories always enabled regardless of probe selection
ALWAYS_ENABLED_CATEGORIES: frozenset[str] = frozenset([
    "Benign (Baseline)",
])

# Model weight tiers for workload warnings
MODEL_WEIGHT: dict[str, str] = {
    "distilgpt2": "light",                              # ~82M params
    "gpt2": "medium",                                   # ~124M params
    "gpt2-medium": "heavy",                             # ~355M params
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": "heavy",     # ~1.1B params
}

# Payload count thresholds per weight tier -- warn when >= this many
PAYLOAD_WARN_THRESHOLDS: dict[str, int] = {
    "light": 15,
    "medium": 10,
    "heavy": 5,
}
